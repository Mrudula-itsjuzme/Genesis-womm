"""The single schedule write path (spine AD-4, AD-5, AD-6, AD-7, AD-8, AD-9).

These run against an in-memory database. The same scenarios run against PostgreSQL in
tests/integration, and the race itself is proven there.
"""

from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest

from app.domain.authz import Actor, Reason
from app.domain.enums import (
    AvailabilityState,
    ConflictType,
    EventStatus,
    OverrideScope,
    Role,
    Severity,
)
from app.domain.lifecycle import (
    EvidenceRequiredError,
    InvalidTransitionError,
    NotAuthorizedError,
)
from app.domain.scheduling import Policy
from app.domain.time import FixedClock
from app.services.errors import (
    ConflictDetectedError,
    DuplicateOverrideError,
    IdempotencyMismatchError,
    InvalidRequestError,
    NotFoundError,
    StaleRevisionError,
)
from app.services.schedule_write import (
    EvidenceInput,
    NewEvent,
    OverrideResult,
    RequestContext,
    ScheduleWriteService,
    WriteResult,
)
from tests.fakes import InMemoryDatabase, SequentialIds

IST = timezone(timedelta(hours=5, minutes=30))
NOW = datetime(2026, 10, 10, 4, 0, tzinfo=UTC)
E = EventStatus

CLUB_A, CLUB_B = UUID(int=101), UUID(int=102)
HALL, LAB, CERTIFIED = UUID(int=201), UUID(int=202), UUID(int=203)
ORGANIZER = Actor(user_id=UUID(int=11), memberships={CLUB_A: Role.ORGANIZER})
CLUB_ADMIN = Actor(user_id=UUID(int=12), memberships={CLUB_A: Role.CLUB_ADMIN})
OTHER_CLUB = Actor(user_id=UUID(int=13), memberships={CLUB_B: Role.ORGANIZER})
OTHER_ADMIN = Actor(user_id=UUID(int=14), memberships={CLUB_B: Role.CLUB_ADMIN})
CAMPUS = Actor(user_id=UUID(int=15), campus_admin=True)
STRANGER = Actor(user_id=UUID(int=16))
PROOF = EvidenceInput(
    kind="EMAIL_REFERENCE", reference="archive/2026-10-09/venue-ok", issuer="OSA", captured_at=NOW
)


def at(hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 10, 20, hour, minute, tzinfo=IST)


@dataclass
class World:
    db: InMemoryDatabase
    svc: ScheduleWriteService
    ids: SequentialIds


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
    svc = ScheduleWriteService(
        db.uow, clock=FixedClock(NOW), ids=ids, policy=Policy(campus_gap=timedelta(minutes=120))
    )
    return World(db, svc, ids)


def ctx(actor: Actor, key: str | None = None, request_id: str = "req-1") -> RequestContext:
    return RequestContext(actor=actor, request_id=request_id, idempotency_key=key)


Slot = tuple[int, int]


def new_event(
    start: Slot = (10, 0),
    end: Slot = (12, 0),
    *,
    venue: UUID | None = HALL,
    club: UUID = CLUB_A,
    title: str = "Robotics Demo Day",
) -> NewEvent:
    return NewEvent(
        club_id=club, title=title, start_at=at(*start), end_at=at(*end), resource_id=venue
    )


def draft(
    w: World,
    actor: Actor = ORGANIZER,
    *,
    start: Slot = (10, 0),
    end: Slot = (12, 0),
    venue: UUID | None = HALL,
    club: UUID = CLUB_A,
) -> WriteResult:
    return w.svc.create_event(ctx(actor), new_event(start, end, venue=venue, club=club))


def advance(w: World, event: WriteResult, *steps: tuple[EventStatus, Actor]) -> WriteResult:
    for target, actor in steps:
        evidence = PROOF if target is E.CONFIRMED else None
        event = w.svc.transition_event(
            ctx(actor),
            event.event.id,
            target,
            expected_revision=event.event.revision,
            evidence=evidence,
        )
    return event


def submitted(
    w: World,
    actor: Actor = ORGANIZER,
    *,
    start: Slot = (10, 0),
    end: Slot = (12, 0),
    venue: UUID | None = HALL,
    club: UUID = CLUB_A,
) -> WriteResult:
    created = draft(w, actor, start=start, end=end, venue=venue, club=club)
    return advance(w, created, (E.PROPOSED, actor), (E.SUBMITTED, actor))


def confirmed(
    w: World,
    actor: Actor = ORGANIZER,
    *,
    start: Slot = (10, 0),
    end: Slot = (12, 0),
    venue: UUID | None = HALL,
    club: UUID = CLUB_A,
) -> WriteResult:
    """An event taken all the way to CONFIRMED the legitimate way."""
    ready = submitted(w, actor, start=start, end=end, venue=venue, club=club)
    return advance(w, ready, (E.CONFIRMED, CAMPUS))


def waive(
    w: World,
    scope: OverrideScope,
    a: UUID,
    b: UUID,
    *,
    actor: Actor = CAMPUS,
    reason: str = "Approved by the registrar",
    key: str | None = None,
    request_id: str = "req-1",
) -> OverrideResult:
    return w.svc.create_override(
        ctx(actor, key, request_id), scope=scope, event_a_id=a, event_b_id=b, reason=reason
    )


def types(result: WriteResult) -> list[ConflictType]:
    return [c.type for c in result.conflicts]


# ---- creating a tentative proposal ----------------------------------------------------


def test_a_new_event_is_a_draft_at_revision_one_created_by_the_actor(world: World) -> None:
    result = draft(world)
    event = result.event
    assert (event.status, event.revision) == (E.DRAFT, 1)
    assert event.created_by == ORGANIZER.user_id
    assert event.club_id == CLUB_A
    assert (event.created_at, event.updated_at) == (NOW, NOW)
    assert event.verified_by is None
    assert world.db.state.events[event.id] == event


def test_a_proposal_is_not_a_booking_so_an_unconfirmed_venue_is_reported_unknown(
    world: World,
) -> None:
    result = draft(world)
    assert types(result) == [ConflictType.UNKNOWN_AVAILABILITY]
    assert result.conflicts[0].severity is Severity.INFO


def test_a_venue_with_confirmed_availability_has_nothing_to_report(world: World) -> None:
    assert draft(world, venue=CERTIFIED).conflicts == ()


def test_an_event_with_no_venue_yet_is_allowed(world: World) -> None:
    result = draft(world, venue=None)
    assert result.event.resource_id is None
    assert result.conflicts == ()


def test_creating_an_event_writes_a_revision_and_an_audit_row(world: World) -> None:
    event = draft(world).event
    (revision,) = world.db.state.revisions
    assert (revision.event_id, revision.revision, revision.previous) == (event.id, 1, None)
    assert revision.current["status"] == "DRAFT"
    (audit,) = world.db.state.audit
    assert (audit.action, audit.outcome, audit.via, audit.request_id) == (
        "CREATE_EVENT",
        "SUCCESS",
        "USER",
        "req-1",
    )
    assert (audit.actor_id, audit.entity_type, audit.entity_id) == (
        ORGANIZER.user_id,
        "event",
        event.id,
    )


@pytest.mark.parametrize("actor", [STRANGER, OTHER_CLUB])
def test_only_a_member_of_the_club_can_create_its_events(world: World, actor: Actor) -> None:
    with pytest.raises(NotAuthorizedError):
        draft(world, actor)
    assert world.db.state.events == {}


def test_a_campus_admin_can_create_an_event_for_any_club(world: World) -> None:
    assert draft(world, CAMPUS, club=CLUB_B).event.club_id == CLUB_B


def test_an_agent_acting_for_an_organizer_cannot_create_an_event(world: World) -> None:
    with pytest.raises(NotAuthorizedError) as refused:
        draft(world, replace(ORGANIZER, via_agent=True))
    assert refused.value.decision.reason is Reason.AGENT_NOT_ALLOWED


def test_an_unknown_venue_or_club_is_not_found(world: World) -> None:
    with pytest.raises(NotFoundError):
        draft(world, venue=UUID(int=999))
    with pytest.raises(NotFoundError):
        draft(world, CAMPUS, club=UUID(int=998))
    assert world.db.state.events == {}


def test_overlapping_proposals_both_save_and_the_second_carries_warnings(world: World) -> None:
    first = draft(world)
    second = draft(world, OTHER_CLUB, club=CLUB_B, start=(11, 0), end=(13, 0))
    # Another club's DRAFT is private, so nothing is reported against it.
    assert ConflictType.TENTATIVE_OVERLAP not in types(second)
    advance(world, first, (E.PROPOSED, ORGANIZER))
    third = draft(world, OTHER_CLUB, club=CLUB_B, start=(10, 30), end=(11, 30))
    assert ConflictType.TENTATIVE_OVERLAP in types(third)
    assert all(c.severity is not Severity.BLOCKING for c in third.conflicts)
    assert len(world.db.state.events) == 3


# ---- lifecycle ------------------------------------------------------------------------


def test_the_full_path_to_confirmed_bumps_the_revision_each_step(world: World) -> None:
    created = draft(world)
    proposed = advance(world, created, (E.PROPOSED, ORGANIZER))
    submitted_ = advance(world, proposed, (E.SUBMITTED, ORGANIZER))
    done = advance(world, submitted_, (E.CONFIRMED, CAMPUS))
    assert [r.event.revision for r in (created, proposed, submitted_, done)] == [1, 2, 3, 4]
    assert [r.event.status for r in (created, proposed, submitted_, done)] == [
        E.DRAFT,
        E.PROPOSED,
        E.SUBMITTED,
        E.CONFIRMED,
    ]
    revisions = [r.revision for r in world.db.state.revisions]
    assert revisions == [1, 2, 3, 4]


def test_confirming_records_the_verifier_the_time_and_the_evidence(world: World) -> None:
    event = confirmed(world).event
    assert event.verified_by == CAMPUS.user_id
    assert event.verified_at == NOW
    assert event.evidence_id is not None
    evidence = world.db.state.evidence[event.evidence_id]
    assert (evidence.kind, evidence.recorded_by) == ("EMAIL_REFERENCE", CAMPUS.user_id)
    assert evidence.reference == PROOF.reference


def test_confirming_without_evidence_is_refused_and_changes_nothing(world: World) -> None:
    ready = submitted(world)
    with pytest.raises(EvidenceRequiredError):
        world.svc.transition_event(
            ctx(CAMPUS), ready.event.id, E.CONFIRMED, expected_revision=ready.event.revision
        )
    assert world.db.state.events[ready.event.id] == ready.event
    assert world.db.state.evidence == {}


@pytest.mark.parametrize("actor", [CLUB_ADMIN, ORGANIZER, OTHER_ADMIN])
def test_only_a_campus_admin_confirms(world: World, actor: Actor) -> None:
    ready = submitted(world)
    with pytest.raises(NotAuthorizedError):
        world.svc.transition_event(
            ctx(actor),
            ready.event.id,
            E.CONFIRMED,
            expected_revision=ready.event.revision,
            evidence=PROOF,
        )
    assert world.db.state.events[ready.event.id].status is E.SUBMITTED


def test_an_invalid_transition_is_refused(world: World) -> None:
    created = draft(world)
    with pytest.raises(InvalidTransitionError):
        world.svc.transition_event(
            ctx(CAMPUS), created.event.id, E.CONFIRMED, expected_revision=1, evidence=PROOF
        )


def test_an_unknown_event_is_not_found(world: World) -> None:
    with pytest.raises(NotFoundError):
        world.svc.transition_event(ctx(CAMPUS), UUID(int=777), E.PROPOSED, expected_revision=1)


def test_a_stale_revision_changes_nothing(world: World) -> None:
    created = draft(world)
    advance(world, created, (E.PROPOSED, ORGANIZER))  # revision is now 2
    with pytest.raises(StaleRevisionError) as stale:
        world.svc.transition_event(
            ctx(CLUB_ADMIN), created.event.id, E.CANCELLED, expected_revision=1
        )
    assert (stale.value.expected, stale.value.actual) == (1, 2)
    assert world.db.state.events[created.event.id].status is E.PROPOSED
    assert len(world.db.state.revisions) == 2


def test_a_status_change_reports_the_availability_of_the_venue_it_holds(world: World) -> None:
    plain = advance(world, draft(world, venue=HALL), (E.PROPOSED, ORGANIZER))
    assert ConflictType.UNKNOWN_AVAILABILITY in types(plain)
    certified = advance(world, draft(world, venue=CERTIFIED), (E.PROPOSED, ORGANIZER))
    assert ConflictType.UNKNOWN_AVAILABILITY not in types(certified)


def test_an_event_that_is_cancelled_gives_up_its_slot(world: World) -> None:
    first = confirmed(world)
    ready = submitted(world, OTHER_CLUB, club=CLUB_B)
    with pytest.raises(ConflictDetectedError):
        advance(world, ready, (E.CONFIRMED, CAMPUS))
    advance(world, first, (E.CANCELLED, CLUB_ADMIN))
    assert advance(world, ready, (E.CONFIRMED, CAMPUS)).event.status is E.CONFIRMED


# ---- blocking happens only when confirming --------------------------------------------


def test_confirming_into_a_same_venue_overlap_is_blocked_with_both_constraints(
    world: World,
) -> None:
    confirmed(world, start=(10, 0), end=(12, 0))
    ready = submitted(world, OTHER_CLUB, club=CLUB_B, start=(11, 0), end=(13, 0))
    with pytest.raises(ConflictDetectedError) as blocked:
        advance(world, ready, (E.CONFIRMED, CAMPUS))
    assert {c.type for c in blocked.value.conflicts} >= {
        ConflictType.VENUE_OVERLAP,
        ConflictType.CAMPUS_GAP_VIOLATION,
    }
    stored = world.db.state.events[ready.event.id]
    assert (stored.status, stored.revision) == (E.SUBMITTED, ready.event.revision)


def test_a_blocked_confirmation_leaves_no_evidence_and_no_revision_behind(world: World) -> None:
    confirmed(world, start=(10, 0), end=(12, 0))
    ready = submitted(world, OTHER_CLUB, club=CLUB_B, start=(11, 0), end=(13, 0))
    evidence_before = dict(world.db.state.evidence)
    revisions_before = len(world.db.state.revisions)
    with pytest.raises(ConflictDetectedError):
        advance(world, ready, (E.CONFIRMED, CAMPUS))
    assert world.db.state.evidence == evidence_before
    assert len(world.db.state.revisions) == revisions_before


def test_a_cross_venue_gap_violation_blocks_the_confirmation(world: World) -> None:
    confirmed(world, start=(9, 0), end=(11, 0), venue=HALL)
    ready = submitted(world, OTHER_CLUB, club=CLUB_B, start=(11, 30), end=(12, 30), venue=LAB)
    with pytest.raises(ConflictDetectedError) as blocked:
        advance(world, ready, (E.CONFIRMED, CAMPUS))
    assert [c.type for c in blocked.value.conflicts if c.severity is Severity.BLOCKING] == [
        ConflictType.CAMPUS_GAP_VIOLATION
    ]


def test_exactly_120_minutes_between_venues_confirms(world: World) -> None:
    confirmed(world, start=(9, 0), end=(11, 0), venue=HALL)
    ready = submitted(world, OTHER_CLUB, club=CLUB_B, start=(13, 0), end=(14, 0), venue=LAB)
    assert advance(world, ready, (E.CONFIRMED, CAMPUS)).event.status is E.CONFIRMED


def test_119_minutes_between_venues_does_not(world: World) -> None:
    confirmed(world, start=(9, 0), end=(11, 0), venue=HALL)
    ready = submitted(world, OTHER_CLUB, club=CLUB_B, start=(12, 59), end=(14, 0), venue=LAB)
    with pytest.raises(ConflictDetectedError):
        advance(world, ready, (E.CONFIRMED, CAMPUS))


def test_proposals_and_submissions_are_never_blocked_by_a_confirmed_event(world: World) -> None:
    confirmed(world, start=(10, 0), end=(12, 0))
    created = draft(world, OTHER_CLUB, club=CLUB_B, start=(11, 0), end=(13, 0))
    proposed = advance(world, created, (E.PROPOSED, OTHER_CLUB))
    assert ConflictType.TENTATIVE_OVERLAP in types(proposed)
    sent = advance(world, proposed, (E.SUBMITTED, OTHER_CLUB))
    assert sent.event.status is E.SUBMITTED
    assert all(c.severity is not Severity.BLOCKING for c in sent.conflicts)


def test_another_clubs_draft_never_blocks_a_confirmation(world: World) -> None:
    draft(world, OTHER_CLUB, club=CLUB_B, start=(10, 0), end=(12, 0))
    assert confirmed(world, start=(10, 0), end=(12, 0)).event.status is E.CONFIRMED


# ---- overrides ------------------------------------------------------------------------


def test_a_campus_gap_override_allows_the_gap_but_never_a_venue_overlap(world: World) -> None:
    anchor = confirmed(world, start=(9, 0), end=(11, 0), venue=HALL)
    near = submitted(world, OTHER_CLUB, club=CLUB_B, start=(11, 30), end=(12, 30), venue=LAB)
    world.svc.create_override(
        ctx(CAMPUS),
        scope=OverrideScope.CAMPUS_GAP,
        event_a_id=anchor.event.id,
        event_b_id=near.event.id,
        reason="Concurrent activities approved by the registrar",
    )
    assert advance(world, near, (E.CONFIRMED, CAMPUS)).event.status is E.CONFIRMED

    clash = submitted(world, OTHER_CLUB, club=CLUB_B, start=(10, 0), end=(12, 0), venue=HALL)
    world.svc.create_override(
        ctx(CAMPUS),
        scope=OverrideScope.CAMPUS_GAP,
        event_a_id=anchor.event.id,
        event_b_id=clash.event.id,
        reason="Gap waived, but the venue is double-booked",
    )
    with pytest.raises(ConflictDetectedError) as blocked:
        advance(world, clash, (E.CONFIRMED, CAMPUS))
    assert ConflictType.VENUE_OVERLAP in {c.type for c in blocked.value.conflicts}
    assert ConflictType.CAMPUS_GAP_VIOLATION not in {
        c.type for c in blocked.value.conflicts if anchor.event.id in c.event_ids
    }


def test_both_overrides_together_let_a_double_booking_through(world: World) -> None:
    anchor = confirmed(world, start=(10, 0), end=(12, 0))
    clash = submitted(world, OTHER_CLUB, club=CLUB_B, start=(11, 0), end=(13, 0))
    for scope in (OverrideScope.CAMPUS_GAP, OverrideScope.VENUE_OVERLAP):
        world.svc.create_override(
            ctx(CAMPUS),
            scope=scope,
            event_a_id=clash.event.id,
            event_b_id=anchor.event.id,
            reason="Joint session approved",
        )
    assert advance(world, clash, (E.CONFIRMED, CAMPUS)).event.status is E.CONFIRMED


def test_an_override_is_stored_in_canonical_order_with_the_actor_as_authority(world: World) -> None:
    a, b = (
        confirmed(world).event,
        submitted(world, OTHER_CLUB, club=CLUB_B, start=(15, 0), end=(16, 0)).event,
    )
    result = world.svc.create_override(
        ctx(CAMPUS),
        scope=OverrideScope.CAMPUS_GAP,
        event_a_id=max(a.id, b.id),
        event_b_id=min(a.id, b.id),
        reason="  Approved by the dean  ",
    )
    record = result.override
    assert record.event_a_id < record.event_b_id
    assert record.authorized_by == CAMPUS.user_id
    assert record.reason == "Approved by the dean"
    assert record.created_at == NOW
    assert world.db.state.overrides == [record]
    assert world.db.state.audit[-1].action == "CREATE_OVERRIDE"


@pytest.mark.parametrize("actor", [CLUB_ADMIN, ORGANIZER, STRANGER])
def test_only_a_campus_admin_creates_an_override(world: World, actor: Actor) -> None:
    a, b = draft(world).event, draft(world, ORGANIZER, start=(14, 0), end=(15, 0)).event
    with pytest.raises(NotAuthorizedError):
        world.svc.create_override(
            ctx(actor), scope=OverrideScope.CAMPUS_GAP, event_a_id=a.id, event_b_id=b.id, reason="x"
        )
    assert world.db.state.overrides == []


def test_an_agent_acting_for_a_campus_admin_cannot_create_an_override(world: World) -> None:
    a, b = draft(world).event, draft(world, ORGANIZER, start=(14, 0), end=(15, 0)).event
    with pytest.raises(NotAuthorizedError) as refused:
        world.svc.create_override(
            ctx(replace(CAMPUS, via_agent=True)),
            scope=OverrideScope.CAMPUS_GAP,
            event_a_id=a.id,
            event_b_id=b.id,
            reason="x",
        )
    assert refused.value.decision.reason is Reason.AGENT_NOT_ALLOWED


@pytest.mark.parametrize("reason", ["", "   "])
def test_an_override_needs_a_reason(world: World, reason: str) -> None:
    a, b = draft(world).event, draft(world, ORGANIZER, start=(14, 0), end=(15, 0)).event
    with pytest.raises(InvalidRequestError):
        world.svc.create_override(
            ctx(CAMPUS),
            scope=OverrideScope.CAMPUS_GAP,
            event_a_id=a.id,
            event_b_id=b.id,
            reason=reason,
        )


def test_an_override_needs_two_different_existing_events(world: World) -> None:
    a = draft(world).event
    with pytest.raises(InvalidRequestError):
        world.svc.create_override(
            ctx(CAMPUS),
            scope=OverrideScope.CAMPUS_GAP,
            event_a_id=a.id,
            event_b_id=a.id,
            reason="x",
        )
    with pytest.raises(NotFoundError):
        world.svc.create_override(
            ctx(CAMPUS),
            scope=OverrideScope.CAMPUS_GAP,
            event_a_id=a.id,
            event_b_id=UUID(int=5),
            reason="x",
        )


def test_the_same_override_cannot_be_created_twice(world: World) -> None:
    a, b = draft(world).event, draft(world, ORGANIZER, start=(14, 0), end=(15, 0)).event
    waive(world, OverrideScope.CAMPUS_GAP, a.id, b.id)
    with pytest.raises(DuplicateOverrideError):
        waive(world, OverrideScope.CAMPUS_GAP, a.id, b.id, request_id="req-2")


# ---- the lock and the order of work ---------------------------------------------------


def test_the_campus_lock_is_taken_before_anything_is_read(world: World) -> None:
    world.db.log.clear()
    draft(world)
    log = world.db.log
    assert log.index("lock") < log.index("read:candidates")
    assert log.index("lock") < log.index("read:overrides")
    assert log[-1] == "commit"


def test_the_lock_comes_before_the_idempotency_check_too(world: World) -> None:
    world.db.log.clear()
    world.svc.create_event(ctx(ORGANIZER, key="k-1"), new_event())
    assert world.db.log.index("lock") < world.db.log.index("read:idempotency")


def test_an_unauthorized_caller_is_refused_before_the_lock_is_taken(world: World) -> None:
    world.db.log.clear()
    with pytest.raises(NotAuthorizedError):
        draft(world, STRANGER)
    assert "lock" not in world.db.log


def test_creating_an_override_also_takes_the_lock(world: World) -> None:
    a, b = draft(world).event, draft(world, ORGANIZER, start=(14, 0), end=(15, 0)).event
    world.db.log.clear()
    world.svc.create_override(
        ctx(CAMPUS), scope=OverrideScope.CAMPUS_GAP, event_a_id=a.id, event_b_id=b.id, reason="x"
    )
    assert world.db.log.index("lock") < world.db.log.index("write:override")


# ---- atomicity ------------------------------------------------------------------------


@pytest.mark.parametrize("step", ["events.insert", "audit.add"])
def test_a_failure_part_way_through_writes_nothing(world: World, step: str) -> None:
    world.db.fail_at = step
    with pytest.raises(RuntimeError, match="injected"):
        draft(world)
    assert world.db.state.events == {}
    assert world.db.state.revisions == []
    assert world.db.state.keys == {}


def test_a_failure_while_confirming_leaves_the_event_and_its_evidence_untouched(
    world: World,
) -> None:
    ready = submitted(world)
    world.db.fail_at = "events.update"
    with pytest.raises(RuntimeError, match="injected"):
        advance(world, ready, (E.CONFIRMED, CAMPUS))
    assert world.db.state.events[ready.event.id] == ready.event
    assert world.db.state.evidence == {}


# ---- audit of refusals ----------------------------------------------------------------


def _forbidden(w: World) -> object:
    return draft(w, STRANGER)


def _unknown_venue(w: World) -> object:
    return draft(w, venue=UUID(int=999))


def _invalid_transition(w: World) -> object:
    created = draft(w)
    return w.svc.transition_event(
        ctx(CAMPUS), created.event.id, E.CONFIRMED, expected_revision=1, evidence=PROOF
    )


def _stale(w: World) -> object:
    created = draft(w)
    return w.svc.transition_event(ctx(ORGANIZER), created.event.id, E.PROPOSED, expected_revision=9)


def _no_evidence(w: World) -> object:
    ready = submitted(w)
    return w.svc.transition_event(
        ctx(CAMPUS), ready.event.id, E.CONFIRMED, expected_revision=ready.event.revision
    )


REFUSED = (
    NotAuthorizedError,
    NotFoundError,
    InvalidTransitionError,
    StaleRevisionError,
    EvidenceRequiredError,
)


@pytest.mark.parametrize(
    ("attempt", "code"),
    [
        (_forbidden, "FORBIDDEN"),
        (_unknown_venue, "NOT_FOUND"),
        (_invalid_transition, "INVALID_TRANSITION"),
        (_stale, "STALE_REVISION"),
        (_no_evidence, "EVIDENCE_REQUIRED"),
    ],
)
def test_a_refused_request_is_audited_with_its_reason(
    world: World, attempt: Callable[[World], object], code: str
) -> None:
    with pytest.raises(REFUSED):
        attempt(world)
    refusals = [a for a in world.db.state.audit if a.outcome == "REFUSED"]
    assert [r.reason_code for r in refusals] == [code]


def test_a_blocked_confirmation_is_audited_as_a_refusal(world: World) -> None:
    confirmed(world, start=(10, 0), end=(12, 0))
    ready = submitted(world, OTHER_CLUB, club=CLUB_B, start=(11, 0), end=(13, 0))
    with pytest.raises(ConflictDetectedError):
        advance(world, ready, (E.CONFIRMED, CAMPUS))
    refusal = world.db.state.audit[-1]
    assert (refusal.outcome, refusal.reason_code, refusal.entity_id) == (
        "REFUSED",
        "CONFLICT_DETECTED",
        ready.event.id,
    )
    assert refusal.actor_id == CAMPUS.user_id


class _ExplodingLog:
    def warning(self, *args: object, **kwargs: object) -> None:
        raise ValueError("I/O operation on closed file")


def test_a_broken_logger_never_hides_the_real_refusal(
    world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    world.db.fail_at = "audit.add"
    monkeypatch.setattr("app.services.schedule_write.log", _ExplodingLog())
    with pytest.raises(NotAuthorizedError):
        draft(world, STRANGER)


def test_a_failed_audit_write_never_hides_the_real_refusal(world: World) -> None:
    world.db.fail_at = "audit.add"
    with pytest.raises(NotAuthorizedError):
        draft(world, STRANGER)


# ---- idempotency ----------------------------------------------------------------------


def test_a_retry_with_the_same_key_returns_the_first_result_and_writes_nothing_more(
    world: World,
) -> None:
    first = world.svc.create_event(ctx(ORGANIZER, key="k-1"), new_event())
    again = world.svc.create_event(ctx(ORGANIZER, key="k-1", request_id="req-2"), new_event())
    assert (first.replayed, again.replayed) == (False, True)
    assert again.event == first.event
    assert again.conflicts == first.conflicts
    assert len(world.db.state.events) == 1
    assert len(world.db.state.revisions) == 1
    assert len(world.db.state.audit) == 1


def test_a_replayed_transition_does_not_move_the_event_again(world: World) -> None:
    created = draft(world)
    args = (created.event.id, E.PROPOSED)
    first = world.svc.transition_event(ctx(ORGANIZER, key="t-1"), *args, expected_revision=1)
    again = world.svc.transition_event(ctx(ORGANIZER, key="t-1"), *args, expected_revision=1)
    assert again.replayed is True
    assert again.event == first.event
    assert world.db.state.events[created.event.id].revision == 2


def test_a_replayed_override_returns_the_same_record(world: World) -> None:
    a, b = draft(world).event, draft(world, ORGANIZER, start=(14, 0), end=(15, 0)).event
    first = waive(world, OverrideScope.CAMPUS_GAP, a.id, b.id, key="o-1")
    again = waive(world, OverrideScope.CAMPUS_GAP, a.id, b.id, key="o-1")
    assert again.replayed is True
    assert again.override == first.override
    assert len(world.db.state.overrides) == 1


def test_reusing_a_key_for_a_different_request_is_refused(world: World) -> None:
    world.svc.create_event(ctx(ORGANIZER, key="k-1"), new_event(title="One"))
    with pytest.raises(IdempotencyMismatchError):
        world.svc.create_event(ctx(ORGANIZER, key="k-1"), new_event(title="Two"))
    assert len(world.db.state.events) == 1


def test_a_key_belongs_to_one_actor(world: World) -> None:
    world.svc.create_event(ctx(ORGANIZER, key="shared"), new_event())
    other = world.svc.create_event(ctx(CAMPUS, key="shared"), new_event(club=CLUB_B))
    assert other.replayed is False
    assert len(world.db.state.events) == 2


def test_a_refused_request_does_not_consume_its_key(world: World) -> None:
    confirmed(world, start=(10, 0), end=(12, 0))
    ready = submitted(world, OTHER_CLUB, club=CLUB_B, start=(11, 0), end=(13, 0))
    with pytest.raises(ConflictDetectedError):
        world.svc.transition_event(
            ctx(CAMPUS, key="c-1"), ready.event.id, E.CONFIRMED, expected_revision=3, evidence=PROOF
        )
    assert ("c-1" in {k for _, k in world.db.state.keys}) is False
    # After the other event is cancelled, the same key and request now succeed.
    other = next(e for e in world.db.state.events.values() if e.club_id == CLUB_A)
    world.svc.transition_event(
        ctx(CLUB_ADMIN), other.id, E.CANCELLED, expected_revision=other.revision
    )
    done = world.svc.transition_event(
        ctx(CAMPUS, key="c-1"), ready.event.id, E.CONFIRMED, expected_revision=3, evidence=PROOF
    )
    assert done.replayed is False
    assert done.event.status is E.CONFIRMED


def test_a_request_without_a_key_is_never_deduplicated(world: World) -> None:
    draft(world)
    draft(world)
    assert len(world.db.state.events) == 2
    assert world.db.state.keys == {}


# ---- times ----------------------------------------------------------------------------


def test_times_are_stored_as_utc_instants_whatever_zone_they_arrive_in(world: World) -> None:
    event = draft(world, start=(10, 0), end=(12, 0)).event
    assert event.start_at == datetime(2026, 10, 20, 4, 30, tzinfo=UTC)
    assert event.start_at.utcoffset() == timedelta(0)


def test_a_naive_or_inverted_interval_cannot_be_created(world: World) -> None:
    with pytest.raises(ValueError, match="offset"):
        world.svc.create_event(
            ctx(ORGANIZER),
            NewEvent(club_id=CLUB_A, title="x", start_at=datetime(2026, 10, 20, 10), end_at=at(12)),
        )
    with pytest.raises(ValueError, match="strictly before"):
        world.svc.create_event(
            ctx(ORGANIZER), NewEvent(club_id=CLUB_A, title="x", start_at=at(12), end_at=at(10))
        )
