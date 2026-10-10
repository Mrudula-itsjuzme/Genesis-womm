"""Mirror of the Core facade's DTOs (`/internal/v1/*` in contracts/core-api.openapi.yaml).

Component names match Core's so a contract test can compare the two documents structurally.
"""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import CampusDatetime
from app.schemas.enums import (
    AgentActionStatus,
    AgentActionType,
    AvailabilityState,
    ConflictConstraint,
    ConflictType,
    EventStatus,
    Severity,
)
from app.schemas.text import Summary


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
    """The minimal view of the other event in a conflict."""

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
    """One violated constraint. Type and severity come from Core and are shown verbatim."""

    type: ConflictType
    severity: Severity
    constraint: ConflictConstraint | None = None
    event_ids: list[UUID] = Field(min_length=1, max_length=2)
    with_event: ConflictEventSummary | None = None
    start_at: CampusDatetime
    end_at: CampusDatetime
    message: str
    override_required: bool


class ConflictCheckOut(BaseModel):
    event_id: UUID | None
    advisory: bool = True
    has_blocking: bool
    conflicts: list[Conflict]
    checked_at: CampusDatetime


class AgentConflictCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID | None = None
    club_id: UUID | None = None
    start_at: CampusDatetime | None = None
    end_at: CampusDatetime | None = None
    resource_id: UUID | None = None


class AgentActionCreate(BaseModel):
    """The Agent's only write: a proposal for a human to confirm."""

    model_config = ConfigDict(extra="forbid")

    type: AgentActionType
    summary: Summary
    target_event_id: UUID | None = None
    expected_revision: int | None = Field(default=None, ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentAction(BaseModel):
    """A proposal. Nothing has happened until a human confirms it."""

    action_id: UUID
    type: AgentActionType
    summary: str
    requires_human_review: Literal[True] = True
    status: AgentActionStatus
    target_event_id: UUID | None
    expected_revision: int | None = None
    payload: dict[str, Any]
    conflicts: list[Conflict] = Field(default_factory=list)
    created_at: CampusDatetime
