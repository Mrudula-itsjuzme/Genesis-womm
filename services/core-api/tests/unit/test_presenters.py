"""Wire projections shared by the public routes and the Agent facade."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.api.presenters import agent_action_out, conflict_check_out
from app.domain.enums import (
    AgentActionStatus,
    AgentActionType,
    AvailabilityState,
    ConflictConstraint,
    ConflictType,
    EventStatus,
    Severity,
)
from app.domain.intervals import Interval
from app.domain.scheduling import Conflict
from app.services.conflict_checks import UNSAVED_CANDIDATE_ID, ConflictCheckResult
from app.services.ports import AgentActionRecord, EventRecord

NOW = datetime(2026, 10, 10, 4, 0, tzinfo=UTC)


def record(event_id: UUID, status: EventStatus = EventStatus.DRAFT) -> EventRecord:
    return EventRecord(
        id=event_id,
        club_id=uuid4(),
        title="Robotics Demo Day",
        description=None,
        start_at=NOW,
        end_at=NOW + timedelta(hours=2),
        resource_id=None,
        expected_attendance=None,
        audience_tags=(),
        status=status,
        revision=1,
        created_by=uuid4(),
        verified_by=None,
        verified_at=None,
        evidence_id=None,
        is_synthetic=True,
        created_at=NOW,
        updated_at=NOW,
    )


def conflict(severity: Severity) -> Conflict:
    return Conflict(
        type=ConflictType.VENUE_OVERLAP
        if severity is Severity.BLOCKING
        else ConflictType.TENTATIVE_OVERLAP,
        severity=severity,
        constraint=ConflictConstraint.VENUE_OVERLAP,
        event_ids=(uuid4(), uuid4()),
        window=Interval(NOW, NOW + timedelta(hours=1)),
        message="overlap",
        override_required=severity is Severity.BLOCKING,
    )


def result(event: EventRecord, *conflicts: Conflict, saved: bool = True) -> ConflictCheckResult:
    return ConflictCheckResult(
        event=event,
        conflicts=conflicts,
        availability=AvailabilityState.UNKNOWN,
        checked_at=NOW,
        saved=saved,
    )


def test_a_saved_event_check_names_the_event_and_the_status_it_was_evaluated_as() -> None:
    event = record(uuid4(), EventStatus.CONFIRMED)

    out = conflict_check_out(result(event))

    assert out.event_id == event.id
    assert out.evaluated_as is EventStatus.CONFIRMED
    assert out.advisory is True
    assert out.checked_at == NOW


def test_an_unsaved_candidate_has_no_event_id_on_the_wire() -> None:
    out = conflict_check_out(result(record(UNSAVED_CANDIDATE_ID), saved=False))

    assert out.event_id is None
    assert out.evaluated_as is EventStatus.DRAFT


def test_has_blocking_is_true_only_when_a_blocking_conflict_exists() -> None:
    event = record(uuid4())

    assert not conflict_check_out(result(event)).has_blocking
    assert not conflict_check_out(result(event, conflict(Severity.WARNING))).has_blocking
    mixed = conflict_check_out(
        result(event, conflict(Severity.WARNING), conflict(Severity.BLOCKING))
    )
    assert mixed.has_blocking
    assert [c.severity for c in mixed.conflicts] == [Severity.WARNING, Severity.BLOCKING]


# ---- agent actions -------------------------------------------------------------------


def an_action(**changes: object) -> AgentActionRecord:
    base = AgentActionRecord(
        id=uuid4(),
        type=AgentActionType.CREATE_EVENT_DRAFT,
        status=AgentActionStatus.PROPOSED,
        summary="Draft a robotics demo day",
        requested_by=uuid4(),
        club_id=uuid4(),
        target_event_id=None,
        expected_revision=None,
        payload={"title": "Demo Day"},
        conflicts=(),
        decided_by=None,
        decided_at=None,
        result_entity_type=None,
        result_entity_id=None,
        created_at=NOW,
        updated_at=NOW,
    )
    return base.but(**changes)


def test_a_proposal_is_projected_as_proposed_and_awaiting_a_human() -> None:
    action = an_action(
        target_event_id=uuid4(), expected_revision=4, conflicts=(conflict(Severity.WARNING),)
    )

    out = agent_action_out(action)

    assert out.action_id == action.id
    assert (out.type, out.status) == (
        AgentActionType.CREATE_EVENT_DRAFT,
        AgentActionStatus.PROPOSED,
    )
    assert out.requires_human_review is True
    assert (out.target_event_id, out.expected_revision) == (action.target_event_id, 4)
    assert out.payload == {"title": "Demo Day"}
    assert [c.severity for c in out.conflicts] == [Severity.WARNING]
    assert out.created_at == NOW


def test_the_projection_never_exposes_who_requested_or_decided_it() -> None:
    out = agent_action_out(
        an_action(
            status=AgentActionStatus.EXECUTED,
            decided_by=uuid4(),
            decided_at=NOW,
            result_entity_type="event",
            result_entity_id=uuid4(),
        )
    )

    assert out.status is AgentActionStatus.EXECUTED
    assert set(out.model_dump()) == {
        "action_id",
        "type",
        "summary",
        "requires_human_review",
        "status",
        "target_event_id",
        "expected_revision",
        "payload",
        "conflicts",
        "created_at",
    }
