from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query

from app.api.deps import session_bearer
from app.api.errors import STUB_OPENAPI, not_implemented, stub_errors
from app.domain.enums import ErrorCode, EventStatus
from app.schemas.events import (
    ConflictCheckOut,
    ConflictCheckRequest,
    EventCreate,
    EventCreatedOut,
    EventList,
    EventOut,
)

router = APIRouter(
    prefix="/api/v1/events",
    tags=["events"],
    dependencies=[Depends(session_bearer)],
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
    openapi_extra=STUB_OPENAPI,
)
def create_event(payload: EventCreate, idempotency_key: IdempotencyKey = None) -> EventCreatedOut:
    not_implemented("Event creation")


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
