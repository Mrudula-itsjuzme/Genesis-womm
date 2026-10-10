"""What a signed-in person does with the Agent's proposals (spine AD-9).

The Agent files them through the facade; the person lists them here and confirms or rejects
with their own session. Nothing the Agent filed has any effect until they do.
"""

from datetime import timedelta
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.container import Container
from app.domain.authz import Actor
from app.domain.enums import (
    AgentActionStatus,
    AgentActionType,
    AvailabilityState,
    EventStatus,
)
from app.domain.scheduling import Policy
from app.domain.time import FixedClock
from app.main import create_app
from app.schemas.agent import AgentAction, AgentActionConfirmOut, AgentActionList
from app.services.agent_actions import AgentActionService, NewAgentAction
from app.services.conflict_checks import ConflictCheckService
from app.services.ports import MembershipIdentity, UserIdentity
from app.services.readiness import ReadinessService
from app.services.schedule_write import NewEvent, RequestContext, ScheduleWriteService
from app.services.sessions import SessionService
from tests.fakes import FakeReadinessProbe, InMemoryDatabase, SequentialIds, make_settings
from tests.unit.test_schedule_write import (
    CAMPUS,
    CERTIFIED,
    CLUB_A,
    CLUB_B,
    HALL,
    LAB,
    NOW,
    ORGANIZER,
    OTHER_CLUB,
    World,
    at,
)

POLICY = Policy(campus_gap=timedelta(minutes=120))
AGENT = Actor(user_id=ORGANIZER.user_id, memberships=ORGANIZER.memberships, via_agent=True)
BASE = "/api/v1/agent-actions"


def identity(actor: Actor, name: str) -> UserIdentity:
    return UserIdentity(
        id=actor.user_id,
        email=f"{name}@example.invalid",
        display_name=name,
        campus_admin=actor.campus_admin,
        memberships=tuple(
            MembershipIdentity(club_id=club, club_name=str(club), role=role)
            for club, role in actor.memberships.items()
        ),
        is_synthetic=True,
    )


class FakeSessions:
    """Maps a bearer token to a person, as the real session service would from the database."""

    def __init__(self) -> None:
        self._by_token = {
            "organizer": identity(ORGANIZER, "organizer"),
            "other": identity(OTHER_CLUB, "other"),
            "campus": identity(CAMPUS, "campus"),
        }

    def resolve_access_token(self, token: str) -> UserIdentity | None:
        return self._by_token.get(token)


def as_person(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def world() -> World:
    db = InMemoryDatabase()
    db.state.clubs = {CLUB_A, CLUB_B}
    db.state.resources = {
        HALL: AvailabilityState.UNKNOWN,
        LAB: AvailabilityState.UNKNOWN,
        CERTIFIED: AvailabilityState.CONFIRMED,
    }
    ids = SequentialIds()
    svc = ScheduleWriteService(db.uow, clock=FixedClock(NOW), ids=ids, policy=POLICY)
    return World(db, svc, ids)


@pytest.fixture
def actions(world: World) -> AgentActionService:
    clock = FixedClock(NOW)
    return AgentActionService(
        world.db.uow,
        checks=ConflictCheckService(world.db.uow, clock=clock, policy=POLICY),
        writes=world.svc,
        clock=clock,
        ids=world.ids,
    )


@pytest.fixture
def client(actions: AgentActionService) -> TestClient:
    container = Container(
        readiness=ReadinessService(FakeReadinessProbe(), "0001"),
        sessions=cast(SessionService, FakeSessions()),
        agent_actions=actions,
    )
    return TestClient(create_app(make_settings(), container), raise_server_exceptions=False)


def file_draft(actions: AgentActionService, **payload: Any) -> UUID:
    """What the Agent does through the facade, ending in a proposal for ORGANIZER."""
    body: dict[str, Any] = {
        "club_id": str(CLUB_A),
        "title": "Robotics Demo Day",
        "start_at": at(10).isoformat(),
        "end_at": at(12).isoformat(),
        "resource_id": str(CERTIFIED),
    }
    body.update(payload)
    command = NewAgentAction(
        type=AgentActionType.CREATE_EVENT_DRAFT, summary="Draft a demo day", payload=body
    )
    filed = actions.file(
        RequestContext(actor=AGENT, request_id=f"agent-{uuid4()}", idempotency_key=None), command
    )
    return filed.action.id


# ---- listing ---------------------------------------------------------------------------


def test_a_person_lists_their_proposals_newest_first_with_a_total(
    client: TestClient, actions: AgentActionService, world: World
) -> None:
    first = file_draft(actions, title="First")
    second = file_draft(actions, title="Second")
    # Same instant under the fixed clock: the order falls back to the id, newest id first.
    expected = [second, first] if second > first else [first, second]

    response = client.get(BASE, headers=as_person("organizer"))

    assert response.status_code == 200, response.text
    out = AgentActionList.model_validate(response.json())
    assert [a.action_id for a in out.items] == expected
    assert (out.total, out.limit, out.offset) == (2, 50, 0)
    assert all(a.status is AgentActionStatus.PROPOSED for a in out.items)


def test_nobody_sees_a_proposal_filed_for_someone_else(
    client: TestClient, actions: AgentActionService
) -> None:
    file_draft(actions)

    for token in ("other", "campus"):
        response = client.get(BASE, headers=as_person(token))
        assert response.status_code == 200
        assert response.json()["items"] == []
        assert response.json()["total"] == 0


def test_listing_filters_by_status_and_pages(
    client: TestClient, actions: AgentActionService
) -> None:
    kept = file_draft(actions, title="Kept")
    rejected = file_draft(actions, title="Rejected")
    client.post(f"{BASE}/{rejected}/reject", headers=as_person("organizer"))

    proposed = client.get(f"{BASE}?status=PROPOSED", headers=as_person("organizer")).json()
    paged = client.get(f"{BASE}?limit=1&offset=1", headers=as_person("organizer")).json()

    assert [a["action_id"] for a in proposed["items"]] == [str(kept)]
    assert proposed["total"] == 1
    assert (len(paged["items"]), paged["total"]) == (1, 2)


@pytest.mark.parametrize(
    "query", ["limit=0", "limit=201", "offset=-1", "status=DONE", "event_id=x"]
)
def test_listing_rejects_out_of_range_parameters(client: TestClient, query: str) -> None:
    response = client.get(f"{BASE}?{query}", headers=as_person("organizer"))

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


# ---- confirming ------------------------------------------------------------------------


def test_confirming_creates_the_event_and_says_what_it_created(
    client: TestClient, actions: AgentActionService, world: World
) -> None:
    action_id = file_draft(actions)

    response = client.post(f"{BASE}/{action_id}/confirm", headers=as_person("organizer"))

    assert response.status_code == 200, response.text
    out = AgentActionConfirmOut.model_validate(response.json())
    assert out.action.status is AgentActionStatus.EXECUTED
    assert out.created_entity_type == "event"
    assert out.created_entity_id in world.db.state.events
    event = world.db.state.events[out.created_entity_id]
    assert (event.status, event.created_by) == (EventStatus.DRAFT, ORGANIZER.user_id)


def test_confirming_twice_returns_the_same_event_and_creates_one(
    client: TestClient, actions: AgentActionService, world: World
) -> None:
    action_id = file_draft(actions)

    first = client.post(f"{BASE}/{action_id}/confirm", headers=as_person("organizer")).json()
    second = client.post(f"{BASE}/{action_id}/confirm", headers=as_person("organizer")).json()

    assert second["created_entity_id"] == first["created_entity_id"]
    assert len(world.db.state.events) == 1


def test_only_the_person_it_was_filed_for_can_confirm(
    client: TestClient, actions: AgentActionService, world: World
) -> None:
    action_id = file_draft(actions)

    for token in ("other", "campus"):
        response = client.post(f"{BASE}/{action_id}/confirm", headers=as_person(token))
        assert response.status_code == 403
        assert response.json()["code"] == "FORBIDDEN"
    assert world.db.state.events == {}


def test_confirming_an_unknown_proposal_is_404(client: TestClient) -> None:
    response = client.post(f"{BASE}/{uuid4()}/confirm", headers=as_person("organizer"))

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_a_rejected_proposal_cannot_be_confirmed(
    client: TestClient, actions: AgentActionService
) -> None:
    action_id = file_draft(actions)
    client.post(f"{BASE}/{action_id}/reject", headers=as_person("organizer"))

    response = client.post(f"{BASE}/{action_id}/confirm", headers=as_person("organizer"))

    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_TRANSITION"


def test_a_proposal_of_a_type_not_built_yet_is_a_clear_422(
    client: TestClient, actions: AgentActionService, world: World
) -> None:
    saved = world.svc.create_event(
        RequestContext(actor=ORGANIZER, request_id="r"),
        NewEvent(club_id=CLUB_A, title="Saved", start_at=at(14), end_at=at(15), resource_id=HALL),
    )
    filed = actions.file(
        RequestContext(actor=AGENT, request_id="a"),
        NewAgentAction(
            type=AgentActionType.RECORD_COMMITMENT,
            summary="Venue said yes",
            target_event_id=saved.event.id,
            payload={"note": "email"},
        ),
    )

    response = client.post(f"{BASE}/{filed.action.id}/confirm", headers=as_person("organizer"))

    assert response.status_code == 422
    assert "not available yet" in response.json()["message"]


# ---- rejecting -------------------------------------------------------------------------


def test_rejecting_marks_it_rejected_and_creates_nothing(
    client: TestClient, actions: AgentActionService, world: World
) -> None:
    action_id = file_draft(actions)

    response = client.post(f"{BASE}/{action_id}/reject", headers=as_person("organizer"))

    assert response.status_code == 200, response.text
    assert AgentAction.model_validate(response.json()).status is AgentActionStatus.REJECTED
    assert world.db.state.events == {}


def test_rejecting_twice_is_the_same_answer(
    client: TestClient, actions: AgentActionService
) -> None:
    action_id = file_draft(actions)

    first = client.post(f"{BASE}/{action_id}/reject", headers=as_person("organizer"))
    second = client.post(f"{BASE}/{action_id}/reject", headers=as_person("organizer"))

    assert (first.status_code, second.status_code) == (200, 200)
    assert second.json() == first.json()


def test_only_the_owner_can_reject_and_an_executed_proposal_cannot_be_rejected(
    client: TestClient, actions: AgentActionService
) -> None:
    action_id = file_draft(actions)

    assert client.post(f"{BASE}/{action_id}/reject", headers=as_person("campus")).status_code == 403
    client.post(f"{BASE}/{action_id}/confirm", headers=as_person("organizer"))
    late = client.post(f"{BASE}/{action_id}/reject", headers=as_person("organizer"))
    assert late.status_code == 409
    assert late.json()["code"] == "INVALID_TRANSITION"


# ---- credentials -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", BASE),
        ("POST", f"{BASE}/{uuid4()}/confirm"),
        ("POST", f"{BASE}/{uuid4()}/reject"),
    ],
)
def test_every_route_needs_a_signed_in_person(client: TestClient, method: str, path: str) -> None:
    anonymous = client.request(method, path)
    stranger = client.request(method, path, headers=as_person("nobody"))

    assert anonymous.status_code == 401
    assert stranger.status_code == 401


# ---- paging, filtering and traceability ------------------------------------------------


def test_pages_walk_the_whole_list_in_order_without_overlap(
    client: TestClient, actions: AgentActionService
) -> None:
    for title in ("One", "Two", "Three"):
        file_draft(actions, title=title)
    everything = client.get(f"{BASE}?limit=200", headers=as_person("organizer")).json()["items"]

    pages = [
        client.get(f"{BASE}?limit=1&offset={n}", headers=as_person("organizer")).json()
        for n in range(4)
    ]

    assert [len(p["items"]) for p in pages] == [1, 1, 1, 0]
    assert [p["items"][0] for p in pages[:3]] == everything
    assert {p["total"] for p in pages} == {3}
    assert [(p["limit"], p["offset"]) for p in pages] == [(1, 0), (1, 1), (1, 2), (1, 3)]


def test_listing_can_be_narrowed_to_proposals_about_one_event(
    client: TestClient, actions: AgentActionService, world: World
) -> None:
    saved = world.svc.create_event(
        RequestContext(actor=ORGANIZER, request_id="r"),
        NewEvent(club_id=CLUB_A, title="Saved", start_at=at(14), end_at=at(15), resource_id=HALL),
    )
    file_draft(actions)
    about_it = actions.file(
        RequestContext(actor=AGENT, request_id="a"),
        NewAgentAction(
            type=AgentActionType.REQUEST_EVENT_CHANGE,
            summary="Move it",
            target_event_id=saved.event.id,
            expected_revision=saved.event.revision,
            payload={"start_at": at(16).isoformat()},
        ),
    ).action

    listed = client.get(f"{BASE}?event_id={saved.event.id}", headers=as_person("organizer")).json()

    assert [a["action_id"] for a in listed["items"]] == [str(about_it.id)]
    assert listed["total"] == 1


def test_the_request_id_follows_a_decision_into_the_audit_trail(
    client: TestClient, actions: AgentActionService, world: World
) -> None:
    confirm_id, reject_id = file_draft(actions, title="A"), file_draft(actions, title="B")

    client.post(
        f"{BASE}/{confirm_id}/confirm",
        headers={**as_person("organizer"), "X-Request-ID": "confirm-trace"},
    )
    client.post(
        f"{BASE}/{reject_id}/reject",
        headers={**as_person("organizer"), "X-Request-ID": "reject-trace"},
    )

    traced = {(a.action, a.request_id, a.via) for a in world.db.state.audit}
    assert ("CONFIRM_AGENT_ACTION", "confirm-trace", "USER") in traced
    assert ("REJECT_AGENT_ACTION", "reject-trace", "USER") in traced
