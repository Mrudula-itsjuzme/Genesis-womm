from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request

from app.api.deps import get_schedule_write_service, require_session_actor
from app.api.errors import STUB_OPENAPI, not_implemented, stub_errors
from app.api.presenters import conflict_out, event_out
from app.domain.authz import Actor
from app.domain.enums import ErrorCode, EventStatus
from app.schemas.events import (
    ConflictCheckOut,
    ConflictCheckRequest,
    EventCreate,
    EventCreatedOut,
    EventList,
    EventOut,
)
from app.services.schedule_write import NewEvent, RequestContext, ScheduleWriteService

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
    openapi_extra=STUB_OPENAPI,
)
def list_events(
    club_id: UUID | None = None,
    status: EventStatus | None = None,
    resource_id: UUID | None = None,
    starts_after: datetime | None = None,
    starts_before: datetime | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> EventList:
    not_implemented("Event listing")


@router.get(
    "/{event_id}",
    response_model=EventOut,
    summary="Get one event",
    responses=stub_errors(ErrorCode.NOT_FOUND),
    openapi_extra=STUB_OPENAPI,
)
def get_event(event_id: UUID) -> EventOut:
    not_implemented("Event lookup")


@router.post(
    "/{event_id}/conflict-check",
    response_model=ConflictCheckOut,
    summary="Check an event, or a hypothetical change to it, for conflicts",
    description=(
        "Advisory: runs the same engine as a write but without the campus lock, so the result "
        "can go stale. Writes re-check inside the transaction."
    ),
    responses=stub_errors(ErrorCode.NOT_FOUND),
    openapi_extra=STUB_OPENAPI,
)
def check_event_conflicts(
    event_id: UUID, payload: ConflictCheckRequest | None = None
) -> ConflictCheckOut:
    not_implemented("Conflict check")
