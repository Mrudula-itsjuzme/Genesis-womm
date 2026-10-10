"""Agent proposals: the Agent files, a human decides (spine AD-9, AD-10).

These run against the in-memory database. The same flows run on PostgreSQL in
tests/integration/test_agent_actions_sql.py.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.domain.authz import Actor, Reason
from app.domain.enums import (
    AgentActionStatus,
    AgentActionType,
    AvailabilityState,
    ConflictType,
    EventStatus,
)
from app.domain.lifecycle import InvalidTransitionError, NotAuthorizedError
from app.domain.scheduling import Policy
from app.domain.time import FixedClock
from app.services.agent_actions import AgentActionService, NewAgentAction
from app.services.conflict_checks import ConflictCheckService
from app.services.errors import IdempotencyMismatchError, InvalidRequestError, NotFoundError
from app.services.ports import AgentActionRecord
from app.services.schedule_write import RequestContext, ScheduleWriteService
from tests.fakes import InMemoryDatabase, SequentialIds
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
    STRANGER,
    at,
    confirmed,
)
from tests.unit.test_schedule_write import World as ScheduleWorld

POLICY = Policy(campus_gap=timedelta(minutes=120))
AGENT = Actor(user_id=ORGANIZER.user_id, memberships=ORGANIZER.memberships, via_agent=True)
E = EventStatus


@dataclass
class World:
    db: InMemoryDatabase
    svc: AgentActionService
    writes: ScheduleWriteService
    ids: SequentialIds

    @property
    def schedule(self) -> ScheduleWorld:
        return ScheduleWorld(self.db, self.writes, self.ids)


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
    clock = FixedClock(NOW)
    writes = ScheduleWriteService(db.uow, clock=clock, ids=ids, policy=POLICY)
    checks = ConflictCheckService(db.uow, clock=clock, policy=POLICY)
    svc = AgentActionService(db.uow, checks=checks, writes=writes, clock=clock, ids=ids)
    return World(db, svc, writes, ids)


def ctx(actor: Actor, key: str | None = None, request_id: str = "req-1") -> RequestContext:
    return RequestContext(actor=actor, request_id=request_id, idempotency_key=key)


def draft_payload(**overrides: Any) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "club_id": str(CLUB_A),
        "title": "Robotics Demo Day",
        "start_at": at(10).isoformat(),
        "end_at": at(12).isoformat(),
        "resource_id": str(CERTIFIED),
    }
    payload.update(overrides)
    return payload


def draft_command(**overrides: Any) -> NewAgentAction:
    return NewAgentAction(
        type=AgentActionType.CREATE_EVENT_DRAFT,
        summary="Draft a robotics demo day",
        payload=draft_payload(**overrides),
    )


def audit(world: World) -> list[tuple[str, str, str | None, str]]:
    return [(a.action, a.outcome, a.reason_code, a.via) for a in world.db.state.audit]


# ---- filing ----------------------------------------------------------------------------


def test_the_agent_files_a_proposal_for_the_user_it_acts_for(world: World) -> None:
    filed = world.svc.file(ctx(AGENT), draft_command())

    action = filed.action
    assert not filed.replayed
    assert action.status is AgentActionStatus.PROPOSED
    assert action.type is AgentActionType.CREATE_EVENT_DRAFT
    assert (action.requested_by, action.club_id) == (ORGANIZER.user_id, CLUB_A)
    assert action.created_at == NOW
    assert action.decided_by is None
    assert world.db.state.agent_actions[action.id] == action


def test_filing_normalizes_the_payload_to_utc_instants(world: World) -> None:
    action = world.svc.file(ctx(AGENT), draft_command()).action

    assert datetime.fromisoformat(action.payload["start_at"]) == at(10)
    assert action.payload["start_at"].endswith("+00:00")
    assert action.payload["club_id"] == str(CLUB_A)
    assert action.payload["audience_tags"] == []


def test_filing_runs_the_dry_run_and_stores_what_it_found(world: World) -> None:
    confirmed(
        world.schedule, actor=OTHER_CLUB, club=CLUB_B, start=(11, 0), end=(13, 0), venue=CERTIFIED
    )

    action = world.svc.file(ctx(AGENT), draft_command()).action

    kinds = {c.type for c in action.conflicts}
    assert ConflictType.TENTATIVE_OVERLAP in kinds
    assert all(c.severity.value != "blocking" for c in action.conflicts)


def test_a_draft_that_clashes_is_still_filed_because_a_draft_never_blocks(world: World) -> None:
    confirmed(
        world.schedule, actor=OTHER_CLUB, club=CLUB_B, start=(10, 0), end=(12, 0), venue=CERTIFIED
    )

    filed = world.svc.file(ctx(AGENT), draft_command())

    assert filed.action.status is AgentActionStatus.PROPOSED
    assert filed.action.conflicts


def test_filing_writes_no_event_takes_no_lock_and_audits_once_as_the_agent(world: World) -> None:
    events_before = dict(world.db.state.events)
    log_before = len(world.db.log)

    world.svc.file(ctx(AGENT), draft_command())

    assert world.db.state.events == events_before
    assert "lock" not in world.db.log[log_before:]
    assert audit(world) == [("FILE_AGENT_ACTION", "SUCCESS", None, "AGENT")]


def test_a_user_with_no_role_in_the_club_cannot_file(world: World) -> None:
    stranger = Actor(user_id=STRANGER.user_id, via_agent=True)

    with pytest.raises(NotAuthorizedError):
        world.svc.file(ctx(stranger), draft_command())
    with pytest.raises(NotAuthorizedError):
        world.svc.file(
            ctx(
                Actor(
                    user_id=OTHER_CLUB.user_id, memberships=OTHER_CLUB.memberships, via_agent=True
                )
            ),
            draft_command(),
        )
    assert world.db.state.agent_actions == {}


def test_a_refused_filing_is_audited_without_leaving_a_proposal(world: World) -> None:
    stranger = Actor(user_id=STRANGER.user_id, via_agent=True)

    with pytest.raises(NotAuthorizedError):
        world.svc.file(ctx(stranger), draft_command())

    assert audit(world) == [("FILE_AGENT_ACTION", "REFUSED", "FORBIDDEN", "AGENT")]


@pytest.mark.parametrize(
    "overrides",
    [
        {"title": ""},
        {"title": 7},
        {"club_id": "not-a-uuid"},
        {"club_id": None},
        {"start_at": "2026-10-20T10:00:00"},
        {"start_at": "tomorrow"},
        {"end_at": at(9).isoformat()},
        {"resource_id": "nope"},
        {"expected_attendance": -1},
        {"expected_attendance": "many"},
        {"audience_tags": "robotics"},
        {"audience_tags": [1, 2]},
        {"status": "CONFIRMED"},
        {"authorized_by": str(CAMPUS.user_id)},
    ],
    ids=lambda o: ",".join(f"{k}={v!r}" for k, v in o.items()),
)
def test_an_invalid_or_authority_bearing_draft_payload_is_refused(
    world: World, overrides: dict[str, Any]
) -> None:
    with pytest.raises(InvalidRequestError):
        world.svc.file(ctx(AGENT), draft_command(**overrides))

    assert world.db.state.agent_actions == {}


def test_a_missing_required_draft_field_is_refused(world: World) -> None:
    for missing in ("club_id", "title", "start_at", "end_at"):
        payload = draft_payload()
        del payload[missing]
        command = NewAgentAction(
            type=AgentActionType.CREATE_EVENT_DRAFT, summary="Draft", payload=payload
        )
        with pytest.raises(InvalidRequestError, match=missing):
            world.svc.file(ctx(AGENT), command)


def test_a_payload_beyond_the_size_cap_is_refused(world: World) -> None:
    with pytest.raises(InvalidRequestError, match="too large"):
        world.svc.file(ctx(AGENT), draft_command(description="x" * 20_000))


def test_an_unknown_venue_in_the_draft_is_not_found(world: World) -> None:
    with pytest.raises(NotFoundError):
        world.svc.file(ctx(AGENT), draft_command(resource_id=str(uuid4())))


def test_an_unknown_club_in_the_draft_is_refused_for_a_campus_admin(world: World) -> None:
    admin_agent = Actor(user_id=CAMPUS.user_id, campus_admin=True, via_agent=True)

    with pytest.raises(NotFoundError):
        world.svc.file(ctx(admin_agent), draft_command(club_id=str(uuid4())))


def test_a_draft_proposal_names_no_target_event_or_revision(world: World) -> None:
    with_target = NewAgentAction(
        type=AgentActionType.CREATE_EVENT_DRAFT,
        summary="Draft",
        payload=draft_payload(),
        target_event_id=uuid4(),
    )
    with_revision = NewAgentAction(
        type=AgentActionType.CREATE_EVENT_DRAFT,
        summary="Draft",
        payload=draft_payload(),
        expected_revision=3,
    )

    for command in (with_target, with_revision):
        with pytest.raises(InvalidRequestError):
            world.svc.file(ctx(AGENT), command)


# ---- the proposals that need features not built yet -----------------------------------


def change_request(target: UUID | None = None, revision: int | None = None) -> NewAgentAction:
    return NewAgentAction(
        type=AgentActionType.REQUEST_EVENT_CHANGE,
        summary="Move it",
        payload={"start_at": "x"},
        target_event_id=target,
        expected_revision=revision,
    )


def test_a_change_request_must_name_a_real_event_and_the_revision_seen(world: World) -> None:
    saved = confirmed(world.schedule, start=(14, 0), end=(15, 0))

    with pytest.raises(InvalidRequestError, match="target_event_id"):
        world.svc.file(ctx(AGENT), change_request())
    with pytest.raises(NotFoundError):
        world.svc.file(ctx(AGENT), change_request(uuid4(), 1))
    with pytest.raises(InvalidRequestError, match="expected_revision"):
        world.svc.file(ctx(AGENT), change_request(saved.event.id))

    filed = world.svc.file(ctx(AGENT), change_request(saved.event.id, saved.event.revision))
    assert filed.action.status is AgentActionStatus.PROPOSED
    assert (filed.action.target_event_id, filed.action.club_id) == (saved.event.id, CLUB_A)
    assert filed.action.expected_revision == saved.event.revision
    assert filed.action.conflicts == ()


def test_a_proposal_against_another_clubs_event_is_refused(world: World) -> None:
    theirs = confirmed(world.schedule, actor=OTHER_CLUB, club=CLUB_B, start=(14, 0), end=(15, 0))
    command = NewAgentAction(
        type=AgentActionType.RECORD_COMMITMENT,
        summary="Venue said yes",
        target_event_id=theirs.event.id,
        payload={"note": "x"},
    )

    with pytest.raises(NotAuthorizedError):
        world.svc.file(ctx(AGENT), command)


# ---- idempotent filing -----------------------------------------------------------------


def test_a_retried_filing_returns_the_same_proposal_once(world: World) -> None:
    first = world.svc.file(ctx(AGENT, key="turn-1-call-1"), draft_command())
    second = world.svc.file(ctx(AGENT, key="turn-1-call-1"), draft_command())

    assert second.replayed
    assert second.action.id == first.action.id
    assert len(world.db.state.agent_actions) == 1
    assert [a[1] for a in audit(world)] == ["SUCCESS"]


def test_the_same_key_with_a_different_body_is_a_mismatch(world: World) -> None:
    world.svc.file(ctx(AGENT, key="k"), draft_command())

    with pytest.raises(IdempotencyMismatchError):
        world.svc.file(ctx(AGENT, key="k"), draft_command(title="A different event"))


def test_the_same_key_for_two_users_is_two_proposals(world: World) -> None:
    other_agent = Actor(
        user_id=OTHER_CLUB.user_id, memberships=OTHER_CLUB.memberships, via_agent=True
    )
    world.svc.file(ctx(AGENT, key="k"), draft_command())
    world.svc.file(ctx(other_agent, key="k"), draft_command(club_id=str(CLUB_B)))

    assert len(world.db.state.agent_actions) == 2


# ---- listing ---------------------------------------------------------------------------


def test_a_person_lists_only_their_own_proposals(world: World) -> None:
    mine = world.svc.file(ctx(AGENT), draft_command()).action
    other_agent = Actor(
        user_id=OTHER_CLUB.user_id, memberships=OTHER_CLUB.memberships, via_agent=True
    )
    world.svc.file(ctx(other_agent), draft_command(club_id=str(CLUB_B)))

    listed, total = world.svc.list_for(ORGANIZER, status=None, event_id=None, limit=50, offset=0)

    assert [a.id for a in listed] == [mine.id]
    assert total == 1


# ---- confirming ------------------------------------------------------------------------


def test_the_owner_confirms_and_the_event_is_created_by_the_human(world: World) -> None:
    action = world.svc.file(ctx(AGENT), draft_command()).action

    done = world.svc.confirm(ctx(ORGANIZER), action.id)

    event = world.db.state.events[done.created_entity_id]
    assert done.created_entity_type == "event"
    assert (event.status, event.created_by, event.club_id) == (E.DRAFT, ORGANIZER.user_id, CLUB_A)
    assert event.title == "Robotics Demo Day"
    assert (done.action.status, done.action.decided_by) == (
        AgentActionStatus.EXECUTED,
        ORGANIZER.user_id,
    )
    assert (done.action.result_entity_type, done.action.result_entity_id) == ("event", event.id)
    assert done.action.decided_at == NOW


def test_confirming_audits_the_decision_as_the_user_not_the_agent(world: World) -> None:
    action = world.svc.file(ctx(AGENT), draft_command()).action

    world.svc.confirm(ctx(ORGANIZER), action.id)

    assert ("CONFIRM_AGENT_ACTION", "SUCCESS", None, "USER") in audit(world)
    assert ("CREATE_EVENT", "SUCCESS", None, "USER") in audit(world)


def test_confirming_twice_creates_one_event_and_returns_the_same_result(world: World) -> None:
    action = world.svc.file(ctx(AGENT), draft_command()).action

    first = world.svc.confirm(ctx(ORGANIZER, request_id="a"), action.id)
    second = world.svc.confirm(ctx(ORGANIZER, request_id="b"), action.id)

    assert second.created_entity_id == first.created_entity_id
    assert second.action == first.action
    assert len(world.db.state.events) == 1


def test_a_retry_after_the_event_was_created_but_before_the_decision_converges(
    world: World,
) -> None:
    """A crash between creating the event and recording the decision must not duplicate it."""
    action = world.svc.file(ctx(AGENT), draft_command()).action
    world.db.fail_at = "agent_actions.decide"
    with pytest.raises(RuntimeError, match="injected"):
        world.svc.confirm(ctx(ORGANIZER), action.id)
    assert world.db.state.agent_actions[action.id].status is AgentActionStatus.PROPOSED
    assert len(world.db.state.events) == 1

    world.db.fail_at = None
    done = world.svc.confirm(ctx(ORGANIZER), action.id)

    assert len(world.db.state.events) == 1
    assert done.created_entity_id in world.db.state.events
    assert done.action.status is AgentActionStatus.EXECUTED


def test_only_the_person_the_proposal_was_filed_for_can_confirm(world: World) -> None:
    action = world.svc.file(ctx(AGENT), draft_command()).action

    for intruder in (CAMPUS, OTHER_CLUB, STRANGER):
        with pytest.raises(NotAuthorizedError) as refused:
            world.svc.confirm(ctx(intruder), action.id)
        assert refused.value.decision.reason in {Reason.NOT_OWNER, Reason.NOT_ORGANIZER}
    assert world.db.state.agent_actions[action.id].status is AgentActionStatus.PROPOSED
    assert world.db.state.events == {}


def test_the_agent_cannot_confirm_its_own_proposal(world: World) -> None:
    action = world.svc.file(ctx(AGENT), draft_command()).action

    with pytest.raises(NotAuthorizedError) as refused:
        world.svc.confirm(ctx(AGENT), action.id)

    assert refused.value.decision.reason is Reason.AGENT_NOT_ALLOWED
    assert world.db.state.events == {}


def test_confirming_an_unknown_proposal_is_not_found(world: World) -> None:
    with pytest.raises(NotFoundError):
        world.svc.confirm(ctx(ORGANIZER), uuid4())


def test_a_user_who_lost_their_role_cannot_confirm_what_was_filed_earlier(world: World) -> None:
    action = world.svc.file(ctx(AGENT), draft_command()).action
    lapsed = Actor(user_id=ORGANIZER.user_id)

    with pytest.raises(NotAuthorizedError):
        world.svc.confirm(ctx(lapsed), action.id)

    assert world.db.state.events == {}
    assert world.db.state.agent_actions[action.id].status is AgentActionStatus.PROPOSED


def test_a_rejected_proposal_cannot_be_confirmed(world: World) -> None:
    action = world.svc.file(ctx(AGENT), draft_command()).action
    world.svc.reject(ctx(ORGANIZER), action.id)

    with pytest.raises(InvalidTransitionError):
        world.svc.confirm(ctx(ORGANIZER), action.id)

    assert world.db.state.events == {}


@pytest.mark.parametrize(
    "kind",
    [
        AgentActionType.REQUEST_EVENT_CHANGE,
        AgentActionType.RECORD_COMMITMENT,
        AgentActionType.CREATE_FOLLOWUP_DRAFT,
    ],
)
def test_proposals_of_types_not_built_yet_stay_proposed_when_confirmed(
    world: World, kind: AgentActionType
) -> None:
    saved = confirmed(world.schedule, start=(14, 0), end=(15, 0))
    action = world.svc.file(
        ctx(AGENT),
        NewAgentAction(
            type=kind,
            summary="Later",
            target_event_id=saved.event.id,
            expected_revision=saved.event.revision,
            payload={"note": "x"},
        ),
    ).action

    with pytest.raises(InvalidRequestError, match="not available yet"):
        world.svc.confirm(ctx(ORGANIZER), action.id)

    assert world.db.state.agent_actions[action.id].status is AgentActionStatus.PROPOSED


# ---- rejecting -------------------------------------------------------------------------


def test_the_owner_rejects_and_nothing_is_created(world: World) -> None:
    action = world.svc.file(ctx(AGENT), draft_command()).action

    rejected = world.svc.reject(ctx(ORGANIZER), action.id)

    assert rejected.status is AgentActionStatus.REJECTED
    assert (rejected.decided_by, rejected.decided_at) == (ORGANIZER.user_id, NOW)
    assert world.db.state.events == {}
    assert ("REJECT_AGENT_ACTION", "SUCCESS", None, "USER") in audit(world)


def test_rejecting_twice_is_the_same_answer(world: World) -> None:
    action = world.svc.file(ctx(AGENT), draft_command()).action

    first = world.svc.reject(ctx(ORGANIZER), action.id)
    second = world.svc.reject(ctx(ORGANIZER), action.id)

    assert second == first


def test_an_executed_proposal_cannot_be_rejected(world: World) -> None:
    action = world.svc.file(ctx(AGENT), draft_command()).action
    world.svc.confirm(ctx(ORGANIZER), action.id)

    with pytest.raises(InvalidTransitionError):
        world.svc.reject(ctx(ORGANIZER), action.id)


def test_only_the_owner_can_reject_and_the_agent_never_can(world: World) -> None:
    action = world.svc.file(ctx(AGENT), draft_command()).action

    for intruder in (CAMPUS, OTHER_CLUB, AGENT):
        with pytest.raises(NotAuthorizedError):
            world.svc.reject(ctx(intruder), action.id)
    assert world.db.state.agent_actions[action.id].status is AgentActionStatus.PROPOSED


def test_rejecting_an_unknown_proposal_is_not_found(world: World) -> None:
    with pytest.raises(NotFoundError):
        world.svc.reject(ctx(ORGANIZER), uuid4())


def test_every_refusal_is_audited_with_its_code(world: World) -> None:
    action = world.svc.file(ctx(AGENT), draft_command()).action
    for attempt in (
        lambda: world.svc.confirm(ctx(CAMPUS), action.id),
        lambda: world.svc.confirm(ctx(ORGANIZER), uuid4()),
        lambda: world.svc.reject(ctx(OTHER_CLUB), action.id),
    ):
        with pytest.raises((NotAuthorizedError, NotFoundError)):
            attempt()

    refusals = [a for a in audit(world) if a[1] == "REFUSED"]
    assert refusals == [
        ("CONFIRM_AGENT_ACTION", "REFUSED", "FORBIDDEN", "USER"),
        ("CONFIRM_AGENT_ACTION", "REFUSED", "NOT_FOUND", "USER"),
        ("REJECT_AGENT_ACTION", "REFUSED", "FORBIDDEN", "USER"),
    ]


def test_a_broken_audit_store_never_hides_the_real_refusal(world: World) -> None:
    action = world.svc.file(ctx(AGENT), draft_command()).action
    world.db.fail_at = "audit.add"

    with pytest.raises(NotAuthorizedError):
        world.svc.confirm(ctx(CAMPUS), action.id)


def test_ids_are_unique_across_proposals(world: World) -> None:
    ids: set[UUID] = set()
    for index in range(3):
        ids.add(
            world.svc.file(ctx(AGENT, key=f"k{index}"), draft_command(title=f"E{index}")).action.id
        )
    assert len(ids) == 3


# ---- losing a race on the decision ----------------------------------------------------


class RacingService(AgentActionService):
    """Lets another request decide the proposal right after this one has read it."""

    def __init__(
        self,
        *args: Any,
        then: Callable[[AgentActionRecord], AgentActionRecord],
        db: InMemoryDatabase,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self._then = then
        self._db = db

    def _owned(self, actor: Actor, action_id: UUID) -> AgentActionRecord:
        record = super()._owned(actor, action_id)
        self._db.state.agent_actions[action_id] = self._then(record)
        return record


def racing(world: World, then: Callable[[AgentActionRecord], AgentActionRecord]) -> RacingService:
    clock = FixedClock(NOW)
    return RacingService(
        world.db.uow,
        checks=ConflictCheckService(world.db.uow, clock=clock, policy=POLICY),
        writes=world.writes,
        clock=clock,
        ids=world.ids,
        then=then,
        db=world.db,
    )


def rejected_by_someone(record: AgentActionRecord) -> AgentActionRecord:
    return record.but(
        status=AgentActionStatus.REJECTED, decided_by=ORGANIZER.user_id, decided_at=NOW
    )


def executed_by_someone(record: AgentActionRecord) -> AgentActionRecord:
    return record.but(
        status=AgentActionStatus.EXECUTED,
        decided_by=ORGANIZER.user_id,
        decided_at=NOW,
        result_entity_type="event",
        result_entity_id=UUID(int=777),
    )


def test_confirming_loses_to_a_rejection_that_landed_first(world: World) -> None:
    action = world.svc.file(ctx(AGENT), draft_command()).action

    with pytest.raises(InvalidTransitionError):
        racing(world, rejected_by_someone).confirm(ctx(ORGANIZER), action.id)

    assert world.db.state.agent_actions[action.id].status is AgentActionStatus.REJECTED


def test_confirming_loses_to_another_confirmation_and_returns_the_winners_result(
    world: World,
) -> None:
    action = world.svc.file(ctx(AGENT), draft_command()).action

    done = racing(world, executed_by_someone).confirm(ctx(ORGANIZER), action.id)

    assert done.action.status is AgentActionStatus.EXECUTED
    assert done.created_entity_id == UUID(int=777)


def test_rejecting_loses_to_a_confirmation_that_landed_first(world: World) -> None:
    action = world.svc.file(ctx(AGENT), draft_command()).action

    with pytest.raises(InvalidTransitionError):
        racing(world, executed_by_someone).reject(ctx(ORGANIZER), action.id)

    assert world.db.state.agent_actions[action.id].status is AgentActionStatus.EXECUTED


def test_rejecting_loses_to_another_rejection_and_agrees_with_it(world: World) -> None:
    action = world.svc.file(ctx(AGENT), draft_command()).action

    rejected = racing(world, rejected_by_someone).reject(ctx(ORGANIZER), action.id)

    assert rejected.status is AgentActionStatus.REJECTED
