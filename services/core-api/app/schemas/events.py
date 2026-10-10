"""Wire schemas for events and conflicts. Never expose ORM rows directly."""

from typing import Annotated, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain.enums import (
    AvailabilityState,
    ConflictConstraint,
    ConflictType,
    EventStatus,
    Severity,
)
from app.domain.time import InvalidIntervalError, ensure_interval
from app.schemas.common import CampusDatetime

Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
AudienceTag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]


class EventCreate(BaseModel):
    """A tentative proposal. There is no writable status: new events start as DRAFT."""

    model_config = ConfigDict(extra="forbid")

    club_id: UUID
    title: Title
    description: str | None = Field(default=None, max_length=4000)
    start_at: CampusDatetime = Field(
        description="Offset-aware ISO 8601. Naive values are rejected."
    )
    end_at: CampusDatetime = Field(description="Exclusive end: intervals are [start_at, end_at).")
    resource_id: UUID | None = Field(
        default=None, description="Preferred venue. Null means the venue is not chosen yet."
    )
    expected_attendance: int | None = Field(default=None, ge=0)
    audience_tags: list[AudienceTag] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def _start_before_end(self) -> Self:
        try:
            ensure_interval(self.start_at, self.end_at)
        except InvalidIntervalError as error:
            raise ValueError(str(error)) from error
        return self


class EventOut(BaseModel):
    id: UUID
    club_id: UUID
    title: str
    description: str | None
    start_at: CampusDatetime
    end_at: CampusDatetime
    resource_id: UUID | None
    expected_attendance: int | None
    audience_tags: list[str]
    status: EventStatus = Field(
        description="Only CONFIRMED means an authorized actor verified it with evidence."
    )
    revision: int = Field(description="Send as expected_revision on every change.")
    venue_availability: AvailabilityState = Field(
        description="UNKNOWN unless evidence-backed commitments say otherwise."
    )
    synthetic: bool = Field(description="True for seeded demo data.")
    created_at: CampusDatetime
    updated_at: CampusDatetime


class ConflictEventSummary(BaseModel):
    """The minimal view of the other event in a conflict. Never includes private planning data."""

    id: UUID
    title: str
    club_id: UUID
    club_name: str
    start_at: CampusDatetime
    end_at: CampusDatetime
    resource_id: UUID | None
    resource_name: str | None
    status: EventStatus
    audience_tags: list[str]


class Conflict(BaseModel):
    """One violated constraint. Type and severity are assigned only by the Core engine."""

    type: ConflictType
    severity: Severity
    constraint: ConflictConstraint | None = Field(
        default=None, description="The independent scheduling constraint that was violated."
    )
    event_ids: list[UUID] = Field(
        min_length=1, max_length=2, description="The candidate first, then the other event."
    )
    with_event: ConflictEventSummary | None = None
    start_at: CampusDatetime = Field(
        description=(
            "Overlaps: start of the shared interval. Campus-gap violations: start of the "
            "required buffer, which is the end_at of whichever event starts first."
        )
    )
    end_at: CampusDatetime = Field(
        description=(
            "Overlaps: end of the shared interval. Campus-gap violations: end of the required "
            "buffer (that end_at plus the gap)."
        )
    )
    message: str
    override_required: bool


class EventCreatedOut(BaseModel):
    event: EventOut
    conflicts: list[Conflict] = Field(
        description="Evaluated when the event was saved. Drafts and proposals always save."
    )


class EventList(BaseModel):
    items: list[EventOut]
    limit: int
    offset: int
    total: int


class ConflictCheckRequest(BaseModel):
    """Check a hypothetical change. Omitted fields use the event's stored values."""

    model_config = ConfigDict(extra="forbid")

    start_at: CampusDatetime | None = None
    end_at: CampusDatetime | None = None
    resource_id: UUID | None = Field(
        default=None,
        description="Omit to keep the stored venue. An explicit null checks with no venue.",
    )


class ConflictCheckOut(BaseModel):
    event_id: UUID | None = Field(description="Null when a not-yet-saved candidate was checked.")
    advisory: bool = Field(
        default=True,
        description="Always true: writes re-check inside the transaction, so this can go stale.",
    )
    has_blocking: bool = Field(description="True when any conflict has severity 'blocking'.")
    conflicts: list[Conflict]
    checked_at: CampusDatetime
