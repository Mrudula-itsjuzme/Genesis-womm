"""The Agent facade's read tools (spine AD-10): same services as the public routes, narrow DTOs."""

from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.clients.delegation import PyJwtDelegationService
from app.container import Container
from app.domain.authz import Actor
from app.domain.enums import AvailabilityState, EventStatus
from app.domain.scheduling import Policy
from app.domain.time import FixedClock
from app.main import create_app
from app.schemas.events import ConflictCheckOut, EventOut
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


# ---- the one facade route still to build ----------------------------------------------


def test_filing_an_action_still_requires_both_credentials_before_it_says_not_implemented(
    client: TestClient,
) -> None:
    body = {"type": "CREATE_EVENT_DRAFT", "summary": "Draft a demo day"}

    unauthenticated = client.post("/internal/v1/agent-actions", json=body)
    authenticated = client.post(
        "/internal/v1/agent-actions", json=body, headers=as_agent_for(ORGANIZER)
    )

    assert unauthenticated.status_code == 401
    assert authenticated.status_code == 501
