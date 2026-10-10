"""The schedule write path on PostgreSQL 18: the same service, real transactions (spine AD-4/8)."""

from dataclasses import replace
from datetime import UTC, datetime

import pytest
from sqlalchemy import text

from app.domain.enums import ConflictType, OverrideScope
from app.domain.lifecycle import NotAuthorizedError
from app.repositories.unit_of_work import SqlUnitOfWork
from app.services.errors import ConflictDetectedError, IdempotencyMismatchError, StaleRevisionError
from app.services.schedule_write import NewEvent
from tests.integration.support import NOW
from tests.integration.world import (
    PROOF,
    E,
    World,
    advance,
    at,
    confirmed,
    ctx,
    draft,
    submitted,
)

pytestmark = pytest.mark.integration

# ---- AGENTS.md 10.1: creating, detecting, confirming ----------------------------------


def test_a_tentative_proposal_is_stored_with_its_history(world: World) -> None:
    result = draft(world)
    assert result.event.status is E.DRAFT
    assert world.count("events") == 1
    assert world.count("event_revisions", f"event_id = '{result.event.id}' AND revision = 1") == 1
    assert world.count("audit_events", "action = 'CREATE_EVENT' AND outcome = 'SUCCESS'") == 1
    with world.engine.connect() as conn:
        row = conn.execute(
            text("SELECT status, revision, start_at, created_by FROM core.events")
        ).one()
    assert (row.status, row.revision) == ("DRAFT", 1)
    assert row.start_at == datetime(2026, 10, 20, 4, 30, tzinfo=UTC)
    assert row.created_by == world.organizer.user_id


def test_overlapping_tentative_proposals_both_save_with_warnings(world: World) -> None:
    advance(world, draft(world), (E.PROPOSED, world.organizer))
    second = draft(world, world.other, club=world.club_b, start=(11, 0), end=(13, 0))
    third = advance(world, second, (E.PROPOSED, world.other))
    assert ConflictType.TENTATIVE_OVERLAP in {c.type for c in third.conflicts}
    assert world.count("events") == 2


def test_confirming_into_a_same_venue_overlap_is_refused_and_leaves_no_trace(world: World) -> None:
    confirmed(world, start=(10, 0), end=(12, 0))
    ready = submitted(world, world.other, club=world.club_b, start=(11, 0), end=(13, 0))
    evidence_before = world.count("evidence_records")
    revisions_before = world.count("event_revisions")
    with pytest.raises(ConflictDetectedError) as blocked:
        advance(world, ready, (E.CONFIRMED, world.campus))
    assert {ConflictType.VENUE_OVERLAP, ConflictType.CAMPUS_GAP_VIOLATION} <= {
        c.type for c in blocked.value.conflicts
    }
    with world.engine.connect() as conn:
        status, revision = conn.execute(
            text("SELECT status, revision FROM core.events WHERE id = :id"), {"id": ready.event.id}
        ).one()
    assert (status, revision) == ("SUBMITTED", ready.event.revision)
    assert world.count("evidence_records") == evidence_before
    assert world.count("event_revisions") == revisions_before
    # The refusal itself is kept: the main transaction rolled back, the audit row did not.
    assert (
        world.count("audit_events", "outcome = 'REFUSED' AND reason_code = 'CONFLICT_DETECTED'")
        == 1
    )


def test_a_cross_venue_gap_blocks_at_119_minutes_and_passes_at_120(world: World) -> None:
    confirmed(world, start=(9, 0), end=(11, 0), venue=world.hall)
    too_close = submitted(
        world, world.other, club=world.club_b, start=(12, 59), end=(14, 0), venue=world.lab
    )
    with pytest.raises(ConflictDetectedError):
        advance(world, too_close, (E.CONFIRMED, world.campus))
    just_right = submitted(
        world, world.other, club=world.club_b, start=(13, 0), end=(14, 0), venue=world.lab
    )
    assert advance(world, just_right, (E.CONFIRMED, world.campus)).event.status is E.CONFIRMED


def test_a_campus_gap_override_never_lets_a_venue_double_booking_through(world: World) -> None:
    anchor = confirmed(world, start=(10, 0), end=(12, 0))
    clash = submitted(world, world.other, club=world.club_b, start=(11, 0), end=(13, 0))
    world.svc.create_override(
        ctx(world.campus),
        scope=OverrideScope.CAMPUS_GAP,
        event_a_id=anchor.event.id,
        event_b_id=clash.event.id,
        reason="Gap waived by the registrar",
    )
    with pytest.raises(ConflictDetectedError) as blocked:
        advance(world, clash, (E.CONFIRMED, world.campus))
    assert ConflictType.VENUE_OVERLAP in {c.type for c in blocked.value.conflicts}
    world.svc.create_override(
        ctx(world.campus),
        scope=OverrideScope.VENUE_OVERLAP,
        event_a_id=clash.event.id,
        event_b_id=anchor.event.id,
        reason="Joint session approved",
    )
    assert advance(world, clash, (E.CONFIRMED, world.campus)).event.status is E.CONFIRMED
    assert world.count("schedule_overrides") == 2


def test_a_confirmation_stores_who_verified_it_and_on_what_evidence(world: World) -> None:
    event = confirmed(world).event
    with world.engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT e.status, e.verified_by, e.verified_at, v.reference, v.recorded_by "
                "FROM core.events e JOIN core.evidence_records v ON v.id = e.evidence_id "
                "WHERE e.id = :id"
            ),
            {"id": event.id},
        ).one()
    assert row.status == "CONFIRMED"
    assert row.verified_by == world.campus.user_id
    assert row.verified_at == NOW
    assert (row.reference, row.recorded_by) == (PROOF.reference, world.campus.user_id)


def test_a_cancelled_event_gives_up_its_slot(world: World) -> None:
    first = confirmed(world)
    ready = submitted(world, world.other, club=world.club_b)
    with pytest.raises(ConflictDetectedError):
        advance(world, ready, (E.CONFIRMED, world.campus))
    advance(world, first, (E.CANCELLED, world.club_admin))
    assert advance(world, ready, (E.CONFIRMED, world.campus)).event.status is E.CONFIRMED


# ---- authorization, staleness and retries ---------------------------------------------


def test_only_a_campus_admin_confirms_and_the_refusal_is_audited(world: World) -> None:
    ready = submitted(world)
    with pytest.raises(NotAuthorizedError):
        world.svc.transition_event(
            ctx(world.club_admin),
            ready.event.id,
            E.CONFIRMED,
            expected_revision=ready.event.revision,
            evidence=PROOF,
        )
    assert world.count("audit_events", "outcome = 'REFUSED' AND reason_code = 'FORBIDDEN'") == 1


def test_an_agent_acting_for_an_organizer_cannot_create_an_event(world: World) -> None:
    agent = replace(world.organizer, via_agent=True)
    with pytest.raises(NotAuthorizedError):
        draft(world, agent)
    assert world.count("events") == 0
    assert world.count("audit_events", "via = 'AGENT' AND outcome = 'REFUSED'") == 1


def test_a_stale_revision_changes_nothing(world: World) -> None:
    created = draft(world)
    advance(world, created, (E.PROPOSED, world.organizer))
    with pytest.raises(StaleRevisionError):
        world.svc.transition_event(
            ctx(world.club_admin), created.event.id, E.CANCELLED, expected_revision=1
        )
    with world.engine.connect() as conn:
        assert conn.execute(text("SELECT status FROM core.events")).scalar_one() == "PROPOSED"


def test_a_retried_request_writes_once(world: World) -> None:
    command = NewEvent(
        club_id=world.club_a,
        title="Retry me",
        start_at=at(10),
        end_at=at(12),
        resource_id=world.hall,
    )
    first = world.svc.create_event(ctx(world.organizer, key="k-1"), command)
    again = world.svc.create_event(ctx(world.organizer, key="k-1", request_id="req-2"), command)
    assert (first.replayed, again.replayed) == (False, True)
    assert again.event == first.event
    assert again.conflicts == first.conflicts
    assert world.count("events") == 1
    assert world.count("audit_events", "outcome = 'SUCCESS'") == 1
    assert world.count("idempotency_keys") == 1


def test_a_reused_key_for_a_different_request_is_refused(world: World) -> None:
    world.svc.create_event(
        ctx(world.organizer, key="k-1"),
        NewEvent(
            club_id=world.club_a,
            title="One",
            start_at=at(10),
            end_at=at(12),
            resource_id=world.hall,
        ),
    )
    with pytest.raises(IdempotencyMismatchError):
        world.svc.create_event(
            ctx(world.organizer, key="k-1"),
            NewEvent(
                club_id=world.club_a,
                title="Two",
                start_at=at(10),
                end_at=at(12),
                resource_id=world.hall,
            ),
        )
    assert world.count("events") == 1


# ---- atomicity ------------------------------------------------------------------------


def test_a_failure_after_the_event_is_written_rolls_the_event_back(world: World) -> None:
    class Broken(SqlUnitOfWork):
        def commit(self) -> None:
            raise RuntimeError("connection lost at commit")

    svc = world.service_over(lambda: Broken(world.factory))
    with pytest.raises(RuntimeError, match="connection lost"):
        svc.create_event(
            ctx(world.organizer),
            NewEvent(
                club_id=world.club_a,
                title="Lost",
                start_at=at(10),
                end_at=at(12),
                resource_id=world.hall,
            ),
        )
    assert world.count("events") == 0
    assert world.count("event_revisions") == 0
    assert world.count("idempotency_keys") == 0
