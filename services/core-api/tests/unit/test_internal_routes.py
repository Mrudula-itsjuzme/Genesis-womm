"""The Agent facade's read tools (spine AD-10): same services as the public routes, narrow DTOs."""

from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.clients.delegation import PyJwtDelegationService
from app.container import Container
from app.domain.authz import Actor
from app.domain.enums import AgentActionStatus, AgentActionType, AvailabilityState, EventStatus
from app.domain.scheduling import Policy
from app.domain.time import FixedClock
from app.main import create_app
from app.schemas.agent import AgentAction
from app.schemas.events import ConflictCheckOut, EventOut
from app.services.agent_actions import AgentActionService
from app.services.conflict_checks import ConflictCheckService
from app.services.delegation import DelegationService
from app.services.event_reads import EventReadService
from app.services.readiness import ReadinessService
from app.services.schedule_write import ScheduleWriteService
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
    confirmed,
    draft,
)

INTERNAL_KEY = "i" * 40
DELEGATION_KEY = "d" * 40
CHECK = "/internal/v1/agent-tools/check_event_conflicts"
EVENT = "/internal/v1/agent-tools/events/{event_id}"
POLICY = Policy(campus_gap=timedelta(minutes=120))


@pytest.fixture
def world() -> World:
    db = InMemoryDatabase()
    db.state.clubs = {CLUB_A, CLUB_B}
    db.state.resources = {
        HALL: AvailabilityState.UNKNOWN,
        LAB: AvailabilityState.UNKNOWN,
        CERTIFIED: AvailabilityState.CONFIRMED,
    }
    for actor in (ORGANIZER, OTHER_CLUB, CAMPUS):
        db.state.actors[actor.user_id] = actor
    ids = SequentialIds()
    svc = ScheduleWriteService(db.uow, clock=FixedClock(NOW), ids=ids, policy=POLICY)
    return World(db, svc, ids)


@pytest.fixture
def client(world: World) -> TestClient:
    db = world.db
    container = Container(
        readiness=ReadinessService(FakeReadinessProbe(), "0001"),
        delegation=DelegationService(db.uow, PyJwtDelegationService(DELEGATION_KEY)),
        conflict_checks=ConflictCheckService(db.uow, clock=FixedClock(NOW), policy=POLICY),
        event_reads=EventReadService(db.uow),
        agent_actions=AgentActionService(
            db.uow,
            checks=ConflictCheckService(db.uow, clock=FixedClock(NOW), policy=POLICY),
            writes=world.svc,
            clock=FixedClock(NOW),
            ids=world.ids,
        ),
        internal_api_key=INTERNAL_KEY,
    )
    app = create_app(make_settings(), container)
    return TestClient(app, raise_server_exceptions=False)


def as_agent_for(actor: Actor, key: str = INTERNAL_KEY) -> dict[str, str]:
    token, _ = PyJwtDelegationService(DELEGATION_KEY).issue(actor.user_id, "req-1")
    return {"X-Internal-Key": key, "Authorization": f"Bearer {token}"}


def candidate_body(club: UUID = CLUB_A, **overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "club_id": str(club),
        "start_at": at(11).isoformat(),
        "end_at": at(13).isoformat(),
        "resource_id": str(CERTIFIED),
    }
    body.update(overrides)
    return body


# ---- credentials -----------------------------------------------------------------------


def test_both_read_tools_refuse_a_caller_without_the_internal_key(
    client: TestClient, world: World
) -> None:
    saved = draft(world)
    bad = as_agent_for(ORGANIZER, key="wrong")

    assert (
        client.post(CHECK, json={"event_id": str(saved.event.id)}, headers=bad).status_code == 401
    )
    assert client.get(EVENT.format(event_id=saved.event.id), headers=bad).status_code == 401


def test_both_read_tools_refuse_a_caller_without_a_delegation(
    client: TestClient, world: World
) -> None:
    saved = draft(world)
    key_only = {"X-Internal-Key": INTERNAL_KEY}

    assert (
        client.post(CHECK, json={"event_id": str(saved.event.id)}, headers=key_only).status_code
        == 401
    )
    assert client.get(EVENT.format(event_id=saved.event.id), headers=key_only).status_code == 401


# ---- check_event_conflicts -------------------------------------------------------------


def test_a_saved_event_check_runs_as_the_delegated_user(client: TestClient, world: World) -> None:
    saved = draft(world, venue=CERTIFIED)
    confirmed(world, actor=OTHER_CLUB, club=CLUB_B, start=(11, 0), end=(13, 0), venue=CERTIFIED)

    response = client.post(
        CHECK,
        json={"event_id": str(saved.event.id), "as_status": "CONFIRMED"},
        headers=as_agent_for(ORGANIZER),
    )

    assert response.status_code == 200, response.text
    out = ConflictCheckOut.model_validate(response.json())
    assert out.event_id == saved.event.id
    assert out.evaluated_as is EventStatus.CONFIRMED
    assert out.has_blocking
    assert out.advisory


def test_an_unsaved_candidate_has_a_null_event_id(client: TestClient) -> None:
    response = client.post(CHECK, json=candidate_body(), headers=as_agent_for(ORGANIZER))

    assert response.status_code == 200, response.text
    out = ConflictCheckOut.model_validate(response.json())
    assert out.event_id is None
    assert out.evaluated_as is EventStatus.DRAFT


def test_the_agent_cannot_check_a_club_its_user_is_not_in(client: TestClient) -> None:
    response = client.post(CHECK, json=candidate_body(club=CLUB_B), headers=as_agent_for(ORGANIZER))

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


def test_the_agent_cannot_check_another_clubs_event_for_conflicts(
    client: TestClient, world: World
) -> None:
    theirs = draft(world, actor=OTHER_CLUB, club=CLUB_B)

    response = client.post(
        CHECK, json={"event_id": str(theirs.event.id)}, headers=as_agent_for(ORGANIZER)
    )

    assert response.status_code == 403


def test_an_unknown_event_is_not_found(client: TestClient) -> None:
    response = client.post(CHECK, json={"event_id": str(uuid4())}, headers=as_agent_for(ORGANIZER))

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"club_id": str(CLUB_A)},
        {"event_id": str(uuid4()), "club_id": str(CLUB_A)},
        {"club_id": str(CLUB_A), "start_at": at(13).isoformat(), "end_at": at(11).isoformat()},
    ],
    ids=["nothing", "club without times", "event and club", "backwards interval"],
)
def test_an_incomplete_or_ambiguous_request_is_a_422(
    client: TestClient, body: dict[str, Any]
) -> None:
    response = client.post(CHECK, json=body, headers=as_agent_for(ORGANIZER))

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_unknown_fields_are_rejected_not_ignored(client: TestClient) -> None:
    body = candidate_body(authorized_by=str(CAMPUS.user_id))

    response = client.post(CHECK, json=body, headers=as_agent_for(ORGANIZER))

    assert response.status_code == 422


def test_a_naive_timestamp_is_rejected(client: TestClient) -> None:
    body = candidate_body(start_at="2026-10-20T11:00:00")

    assert client.post(CHECK, json=body, headers=as_agent_for(ORGANIZER)).status_code == 422


def test_a_check_writes_nothing(client: TestClient, world: World) -> None:
    saved = draft(world)
    commits, events = world.db.commits, dict(world.db.state.events)

    client.post(CHECK, json={"event_id": str(saved.event.id)}, headers=as_agent_for(ORGANIZER))
    client.post(CHECK, json=candidate_body(), headers=as_agent_for(ORGANIZER))

    assert world.db.commits == commits
    assert world.db.state.events == events


# ---- get_event_details -----------------------------------------------------------------


def test_the_agent_reads_an_event_its_user_may_see(client: TestClient, world: World) -> None:
    saved = draft(world, venue=CERTIFIED)

    response = client.get(EVENT.format(event_id=saved.event.id), headers=as_agent_for(ORGANIZER))

    assert response.status_code == 200, response.text
    out = EventOut.model_validate(response.json())
    assert (out.id, out.club_id, out.venue_availability) == (
        saved.event.id,
        CLUB_A,
        AvailabilityState.CONFIRMED,
    )


def test_another_clubs_confirmed_event_is_a_summary_without_private_fields(
    client: TestClient, world: World
) -> None:
    theirs = confirmed(world, actor=OTHER_CLUB, club=CLUB_B, start=(15, 0), end=(17, 0))

    response = client.get(EVENT.format(event_id=theirs.event.id), headers=as_agent_for(ORGANIZER))

    assert response.status_code == 200
    body = response.json()
    assert body["description"] is None
    assert body["expected_attendance"] is None
    assert body["audience_tags"] == []


def test_another_clubs_draft_is_not_readable_by_the_agent(client: TestClient, world: World) -> None:
    theirs = draft(world, actor=OTHER_CLUB, club=CLUB_B)

    response = client.get(EVENT.format(event_id=theirs.event.id), headers=as_agent_for(ORGANIZER))

    assert response.status_code == 403


def test_a_missing_event_is_404(client: TestClient) -> None:
    response = client.get(EVENT.format(event_id=uuid4()), headers=as_agent_for(ORGANIZER))

    assert response.status_code == 404


# ---- file_agent_action: the Agent's only write ---------------------------------------

ACTIONS = "/internal/v1/agent-actions"


def draft_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "type": "CREATE_EVENT_DRAFT",
        "summary": "Draft a robotics demo day",
        "payload": {
            "club_id": str(CLUB_A),
            "title": "Robotics Demo Day",
            "start_at": at(11).isoformat(),
            "end_at": at(13).isoformat(),
            "resource_id": str(CERTIFIED),
        },
    }
    body.update(overrides)
    return body


def test_filing_a_proposal_returns_it_as_proposed_and_creates_nothing(
    client: TestClient, world: World
) -> None:
    response = client.post(ACTIONS, json=draft_body(), headers=as_agent_for(ORGANIZER))

    assert response.status_code == 201, response.text
    out = AgentAction.model_validate(response.json())
    assert out.status is AgentActionStatus.PROPOSED
    assert out.requires_human_review is True
    assert world.db.state.events == {}
    stored = world.db.state.agent_actions[out.action_id]
    assert stored.requested_by == ORGANIZER.user_id


def test_the_proposal_carries_the_dry_run_the_user_will_see(
    client: TestClient, world: World
) -> None:
    confirmed(world, actor=OTHER_CLUB, club=CLUB_B, start=(12, 0), end=(14, 0), venue=CERTIFIED)

    response = client.post(ACTIONS, json=draft_body(), headers=as_agent_for(ORGANIZER))

    assert response.status_code == 201, response.text
    conflicts = response.json()["conflicts"]
    assert {c["type"] for c in conflicts} == {"TENTATIVE_OVERLAP"}
    assert {c["severity"] for c in conflicts} == {"warning"}


def test_a_retried_filing_returns_the_same_proposal(client: TestClient, world: World) -> None:
    headers = {**as_agent_for(ORGANIZER), "Idempotency-Key": "turn-1-call-1"}

    first = client.post(ACTIONS, json=draft_body(), headers=headers)
    second = client.post(ACTIONS, json=draft_body(), headers=headers)

    assert (first.status_code, second.status_code) == (201, 201)
    assert second.json()["action_id"] == first.json()["action_id"]
    assert len(world.db.state.agent_actions) == 1


def test_the_same_key_with_a_different_body_is_a_422_mismatch(client: TestClient) -> None:
    headers = {**as_agent_for(ORGANIZER), "Idempotency-Key": "k"}
    client.post(ACTIONS, json=draft_body(), headers=headers)

    response = client.post(ACTIONS, json=draft_body(summary="Something else"), headers=headers)

    assert response.status_code == 422
    assert response.json()["code"] == "IDEMPOTENCY_MISMATCH"


def test_the_agent_cannot_file_for_a_club_its_user_is_not_in(client: TestClient) -> None:
    body = draft_body()
    body["payload"]["club_id"] = str(CLUB_B)

    response = client.post(ACTIONS, json=body, headers=as_agent_for(ORGANIZER))

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"


@pytest.mark.parametrize(
    "body",
    [
        draft_body(type="CONFIRM_EVENT"),
        draft_body(type="BOOK_EVENT"),
        draft_body(status="EXECUTED"),
        draft_body(authorized_by=str(CAMPUS.user_id)),
        draft_body(summary=""),
        draft_body(payload={"title": "No club or times"}),
        draft_body(payload={**draft_body()["payload"], "status": "CONFIRMED"}),
    ],
    ids=[
        "confirm type",
        "book type",
        "status field",
        "authorized_by field",
        "blank summary",
        "incomplete payload",
        "payload with a status",
    ],
)
def test_nothing_authority_bearing_can_be_filed(client: TestClient, body: dict[str, Any]) -> None:
    response = client.post(ACTIONS, json=body, headers=as_agent_for(ORGANIZER))

    assert response.status_code == 422, response.text
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_filing_requires_both_credentials(client: TestClient) -> None:
    assert client.post(ACTIONS, json=draft_body()).status_code == 401
    assert (
        client.post(
            ACTIONS, json=draft_body(), headers={"X-Internal-Key": INTERNAL_KEY}
        ).status_code
        == 401
    )


def test_a_change_request_keeps_its_type_target_and_revision(
    client: TestClient, world: World
) -> None:
    saved = confirmed(world, start=(14, 0), end=(15, 0))
    body = {
        "type": "REQUEST_EVENT_CHANGE",
        "summary": "Move it an hour later",
        "target_event_id": str(saved.event.id),
        "expected_revision": saved.event.revision,
        "payload": {"start_at": at(15).isoformat()},
    }

    response = client.post(ACTIONS, json=body, headers=as_agent_for(ORGANIZER))

    assert response.status_code == 201, response.text
    out = AgentAction.model_validate(response.json())
    assert out.type is AgentActionType.REQUEST_EVENT_CHANGE
    assert out.target_event_id == saved.event.id
    assert out.expected_revision == saved.event.revision
    assert out.status is AgentActionStatus.PROPOSED


def test_the_request_id_follows_the_proposal_into_the_audit_trail(
    client: TestClient, world: World
) -> None:
    client.post(
        ACTIONS,
        json=draft_body(),
        headers={**as_agent_for(ORGANIZER), "X-Request-ID": "trace-me-123"},
    )

    [row] = world.db.state.audit
    assert (row.action, row.request_id, row.via) == ("FILE_AGENT_ACTION", "trace-me-123", "AGENT")
