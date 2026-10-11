from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request

from app.api.deps import (
    get_change_queries,
    get_conflict_check_service,
    get_event_read_service,
    get_schedule_write_service,
    require_session_actor,
)
from app.api.errors import stub_errors
from app.api.presenters import conflict_check_out, conflict_out, event_out
from app.domain.authz import Actor
from app.domain.enums import ErrorCode, EventStatus
from app.schemas.changes import (
    ApplyChange,
    ChangeAppliedOut,
    ChangeProposalList,
    ChangeProposalOut,
    ChangeRequest,
    DependencyCreate,
    DependencyList,
    DependencyOut,
    ImpactItem,
    ImpactReport,
    StageChange,
)
from app.schemas.events import (
    ConflictCheckOut,
    ConflictCheckRequest,
    EventCreate,
    EventCreatedOut,
    EventList,
    EventOut,
    TransitionRequest,
)
from app.services.change_ports import ChangeRecord, impact_json, record_json
from app.services.change_queries import ChangeQueries
from app.services.codec import conflict_from_json
from app.services.conflict_checks import ConflictCheckService
from app.services.errors import NotFoundError
from app.services.event_reads import EventReadService
from app.services.schedule_write import (
    EvidenceInput,
    NewEvent,
    RequestContext,
    ScheduleWriteService,
)

router = APIRouter(
    prefix="/api/v1/events",
    tags=["events"],
    dependencies=[Depends(require_session_actor)],
)

IdempotencyKey = Annotated[
    str | None,
    Header(alias="Idempotency-Key", max_length=128, description="Makes a retried POST safe."),
]


@router.post(
    "",
    status_code=201,
    response_model=EventCreatedOut,
    summary="Create a tentative event proposal",
    description=(
        "Saves a DRAFT. Drafts and proposals always save; conflicts are returned alongside. "
        "A proposal is not a venue booking."
    ),
    responses=stub_errors(ErrorCode.IDEMPOTENCY_MISMATCH),
)
def create_event(
    payload: EventCreate,
    actor: Annotated[Actor, Depends(require_session_actor)],
    service: Annotated[ScheduleWriteService, Depends(get_schedule_write_service)],
    request: Request,
    idempotency_key: IdempotencyKey = None,
) -> EventCreatedOut:
    result = service.create_event(
        RequestContext(
            actor=actor,
            request_id=str(request.state.request_id),
            idempotency_key=idempotency_key,
        ),
        NewEvent(
            club_id=payload.club_id,
            title=payload.title,
            description=payload.description,
            start_at=payload.start_at,
            end_at=payload.end_at,
            resource_id=payload.resource_id,
            expected_attendance=payload.expected_attendance,
            audience_tags=tuple(payload.audience_tags),
        ),
    )
    return EventCreatedOut(
        event=event_out(result.event, result.venue_availability),
        conflicts=[conflict_out(conflict) for conflict in result.conflicts],
    )


@router.get(
    "",
    response_model=EventList,
    summary="List events visible to the caller",
    responses=stub_errors(),
)
def list_events(
    actor: Annotated[Actor, Depends(require_session_actor)],
    service: Annotated[EventReadService, Depends(get_event_read_service)],
    club_id: UUID | None = None,
    status: EventStatus | None = None,
    resource_id: UUID | None = None,
    starts_after: datetime | None = None,
    starts_before: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EventList:
    views, total = service.list(
        actor,
        club_id=club_id,
        status=status,
        resource_id=resource_id,
        starts_after=starts_after,
        starts_before=starts_before,
        limit=limit,
        offset=offset,
    )
    return EventList(
        items=[event_out(view.event, view.availability) for view in views],
        limit=limit,
        offset=offset,
        total=total,
    )


@router.post(
    "/conflict-check",
    response_model=ConflictCheckOut,
    summary="Preview an unsaved event without creating a draft",
    responses=stub_errors(ErrorCode.NOT_FOUND),
)
def preview_candidate(
    payload: EventCreate,
    actor: Annotated[Actor, Depends(require_session_actor)],
    service: Annotated[ConflictCheckService, Depends(get_conflict_check_service)],
    as_status: EventStatus = EventStatus.DRAFT,
) -> ConflictCheckOut:
    return conflict_check_out(
        service.check_candidate(
            actor,
            club_id=payload.club_id,
            start_at=payload.start_at,
            end_at=payload.end_at,
            resource_id=payload.resource_id,
            as_status=as_status,
        )
    )


@router.get(
    "/{event_id}",
    response_model=EventOut,
    summary="Get one event",
    responses=stub_errors(ErrorCode.NOT_FOUND),
)
def get_event(
    event_id: UUID,
    actor: Annotated[Actor, Depends(require_session_actor)],
    service: Annotated[EventReadService, Depends(get_event_read_service)],
) -> EventOut:
    view = service.get(actor, event_id)
    return event_out(view.event, view.availability)


@router.post(
    "/{event_id}/conflict-check",
    response_model=ConflictCheckOut,
    summary="Check an event, or a hypothetical change to it, for conflicts",
    description=(
        "Advisory: runs the same engine as a write but without the campus lock, so the result "
        "can go stale. Writes re-check inside the transaction."
    ),
    responses=stub_errors(ErrorCode.NOT_FOUND),
)
def check_event_conflicts(
    event_id: UUID,
    actor: Annotated[Actor, Depends(require_session_actor)],
    service: Annotated[ConflictCheckService, Depends(get_conflict_check_service)],
    payload: ConflictCheckRequest | None = None,
) -> ConflictCheckOut:
    if payload is None:
        result = service.check(actor, event_id)
    else:
        fields = payload.model_fields_set
        provided = fields is not None and "resource_id" in fields
        result = service.check(
            actor,
            event_id,
            start_at=payload.start_at,
            end_at=payload.end_at,
            resource_id=payload.resource_id,
            resource_id_was_provided=provided,
            as_status=payload.as_status,
        )
    return conflict_check_out(result)


@router.post(
    "/{event_id}/transitions",
    response_model=EventOut,
    summary="Move an event along its lifecycle",
    description="Only a confirmation can be blocked by a conflict.",
    responses=stub_errors(ErrorCode.NOT_FOUND, ErrorCode.CONFLICT_DETECTED),
)
def transition_event_route(
    event_id: UUID,
    payload: TransitionRequest,
    actor: Annotated[Actor, Depends(require_session_actor)],
    service: Annotated[ScheduleWriteService, Depends(get_schedule_write_service)],
    request: Request,
    idempotency_key: IdempotencyKey = None,
) -> EventOut:
    ctx = RequestContext(
        actor=actor,
        request_id=str(request.state.request_id),
        idempotency_key=idempotency_key,
    )
    evidence_input = None
    if payload.evidence:
        evidence_input = EvidenceInput(
            kind=payload.evidence.kind,
            reference=payload.evidence.reference,
            captured_at=payload.evidence.captured_at,
            issuer=payload.evidence.issuer,
        )

    result = service.transition_event(
        ctx,
        event_id,
        target=payload.target_status,
        expected_revision=payload.expected_revision,
        evidence=evidence_input,
    )
    return event_out(result.event, result.venue_availability)


def change_out(record: ChangeRecord) -> ChangeProposalOut:
    data = record_json(record)
    data["conflicts"] = [conflict_out(conflict_from_json(item)) for item in record.conflicts]
    return ChangeProposalOut.model_validate(data)


def scoped_change(
    queries: ChangeQueries, actor: Actor, event_id: UUID, proposal_id: UUID
) -> ChangeRecord:
    record = queries.get(actor, proposal_id)
    if record.event_id != event_id:
        raise NotFoundError("change proposal", proposal_id)
    return record


@router.post(
    "/{event_id}/impact", response_model=ImpactReport, responses=stub_errors(ErrorCode.NOT_FOUND)
)
def preview_change(
    event_id: UUID,
    payload: ChangeRequest,
    actor: Annotated[Actor, Depends(require_session_actor)],
    queries: Annotated[ChangeQueries, Depends(get_change_queries)],
) -> ImpactReport:
    preview = queries.preview(
        actor, event_id, payload.expected_revision, payload.changes.model_dump(exclude_unset=True)
    )
    return ImpactReport.model_validate(
        {
            "event_id": event_id,
            "base_revision": preview.event.revision,
            "changed_fields": sorted(preview.changes),
            "evaluated_as": preview.candidate.status,
            "conflicts": [conflict_out(item) for item in preview.conflicts],
            "impact": impact_json(preview.impact),
        }
    )


@router.post(
    "/{event_id}/change-proposals",
    status_code=201,
    response_model=ChangeProposalOut,
    response_model_exclude_unset=True,
    responses=stub_errors(ErrorCode.NOT_FOUND, ErrorCode.IDEMPOTENCY_MISMATCH),
)
def stage_change_route(
    event_id: UUID,
    payload: StageChange,
    request: Request,
    actor: Annotated[Actor, Depends(require_session_actor)],
    service: Annotated[ScheduleWriteService, Depends(get_schedule_write_service)],
    idempotency_key: IdempotencyKey = None,
) -> ChangeProposalOut:
    return change_out(
        service.stage_change(
            RequestContext(actor, str(request.state.request_id), idempotency_key),
            event_id,
            expected_revision=payload.expected_revision,
            changes=payload.changes.model_dump(exclude_unset=True),
            reason=payload.reason,
        )
    )


@router.get(
    "/{event_id}/change-proposals",
    response_model=ChangeProposalList,
    response_model_exclude_unset=True,
    responses=stub_errors(ErrorCode.NOT_FOUND),
)
def list_changes(
    event_id: UUID,
    actor: Annotated[Actor, Depends(require_session_actor)],
    queries: Annotated[ChangeQueries, Depends(get_change_queries)],
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ChangeProposalList:
    records, total = queries.list(actor, event_id, limit, offset)
    return ChangeProposalList(
        items=[change_out(item) for item in records], total=total, limit=limit, offset=offset
    )


@router.get(
    "/{event_id}/change-proposals/{proposal_id}",
    response_model=ChangeProposalOut,
    response_model_exclude_unset=True,
    responses=stub_errors(ErrorCode.NOT_FOUND),
)
def get_change(
    event_id: UUID,
    proposal_id: UUID,
    actor: Annotated[Actor, Depends(require_session_actor)],
    queries: Annotated[ChangeQueries, Depends(get_change_queries)],
) -> ChangeProposalOut:
    return change_out(scoped_change(queries, actor, event_id, proposal_id))


@router.post(
    "/{event_id}/change-proposals/{proposal_id}/apply",
    response_model=ChangeAppliedOut,
    responses=stub_errors(
        ErrorCode.NOT_FOUND, ErrorCode.CONFLICT_DETECTED, ErrorCode.IDEMPOTENCY_MISMATCH
    ),
)
def apply_change_route(
    event_id: UUID,
    proposal_id: UUID,
    payload: ApplyChange,
    request: Request,
    actor: Annotated[Actor, Depends(require_session_actor)],
    queries: Annotated[ChangeQueries, Depends(get_change_queries)],
    service: Annotated[ScheduleWriteService, Depends(get_schedule_write_service)],
    idempotency_key: IdempotencyKey = None,
) -> ChangeAppliedOut:
    scoped_change(queries, actor, event_id, proposal_id)
    result = service.apply_change(
        RequestContext(actor, str(request.state.request_id), idempotency_key),
        proposal_id,
        expected_revision=payload.expected_revision,
    )
    record = queries.get(actor, proposal_id)
    return ChangeAppliedOut(
        event=event_out(result.event, result.venue_availability),
        conflicts=[conflict_out(item) for item in result.conflicts],
        impact=[ImpactItem.model_validate(item) for item in record.impact],
    )


@router.get(
    "/{event_id}/dependencies",
    response_model=DependencyList,
    responses=stub_errors(ErrorCode.NOT_FOUND),
)
def list_dependencies(
    event_id: UUID,
    actor: Annotated[Actor, Depends(require_session_actor)],
    queries: Annotated[ChangeQueries, Depends(get_change_queries)],
) -> DependencyList:
    records = queries.items(actor, event_id)
    return DependencyList(
        items=[DependencyOut.model_validate(record_json(item)) for item in records],
        total=len(records),
    )


@router.post(
    "/{event_id}/dependencies",
    status_code=201,
    response_model=DependencyOut,
    responses=stub_errors(ErrorCode.NOT_FOUND, ErrorCode.IDEMPOTENCY_MISMATCH),
)
def register_dependency_route(
    event_id: UUID,
    payload: DependencyCreate,
    request: Request,
    actor: Annotated[Actor, Depends(require_session_actor)],
    service: Annotated[ScheduleWriteService, Depends(get_schedule_write_service)],
    idempotency_key: IdempotencyKey = None,
) -> DependencyOut:
    record = service.register_dependency(
        RequestContext(actor, str(request.state.request_id), idempotency_key),
        event_id,
        kind=payload.kind,
        title=payload.title,
        field_paths=tuple(payload.field_paths),
    )
    return DependencyOut.model_validate(record_json(record))
