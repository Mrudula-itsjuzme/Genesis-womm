"""Safe API projections for service records. ORM objects never reach route responses."""

from app.domain.enums import AvailabilityState, Severity
from app.domain.scheduling import Conflict as DomainConflict
from app.schemas.agent import AgentAction
from app.schemas.events import Conflict, ConflictCheckOut, EventOut
from app.schemas.resources import ResourceOut
from app.services.conflict_checks import ConflictCheckResult
from app.services.ports import AgentActionRecord, EventRecord, ResourceRecord


def event_out(record: EventRecord, availability: AvailabilityState) -> EventOut:
    return EventOut(
        id=record.id,
        club_id=record.club_id,
        title=record.title,
        description=record.description,
        start_at=record.start_at,
        end_at=record.end_at,
        resource_id=record.resource_id,
        expected_attendance=record.expected_attendance,
        audience_tags=list(record.audience_tags),
        status=record.status,
        revision=record.revision,
        venue_availability=availability,
        synthetic=record.is_synthetic,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def conflict_out(conflict: DomainConflict) -> Conflict:
    return Conflict(
        type=conflict.type,
        severity=conflict.severity,
        constraint=conflict.constraint,
        event_ids=list(conflict.event_ids),
        start_at=conflict.window.start,
        end_at=conflict.window.end,
        message=conflict.message,
        override_required=conflict.override_required,
    )


def resource_out(record: ResourceRecord) -> ResourceOut:
    return ResourceOut(
        id=record.id,
        kind=record.kind,
        name=record.name,
        description=record.description,
        location=record.location,
        capacity=record.capacity,
        availability_state=record.availability_state,
        freshness_state=record.freshness_state,
        source_id=record.source_id,
        source_url=record.source_url,
        collected_at=record.collected_at,
        last_checked_at=record.last_checked_at,
        synthetic=record.is_synthetic,
    )


def conflict_check_out(result: ConflictCheckResult) -> ConflictCheckOut:
    return ConflictCheckOut(
        event_id=result.event.id if result.saved else None,
        evaluated_as=result.event.status,
        advisory=True,
        has_blocking=any(c.severity is Severity.BLOCKING for c in result.conflicts),
        conflicts=[conflict_out(c) for c in result.conflicts],
        checked_at=result.checked_at,
    )


def agent_action_out(record: AgentActionRecord) -> AgentAction:
    """A proposal as clients see it. Who filed or decided it stays server-side."""
    return AgentAction(
        action_id=record.id,
        type=record.type,
        summary=record.summary,
        status=record.status,
        target_event_id=record.target_event_id,
        expected_revision=record.expected_revision,
        payload=record.payload,
        conflicts=[conflict_out(c) for c in record.conflicts],
        created_at=record.created_at,
    )
