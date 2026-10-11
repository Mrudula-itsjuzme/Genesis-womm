"""Strict public contracts for two-phase changes and reported dependencies."""

from typing import Annotated, Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

from app.domain.enums import EventStatus
from app.schemas.common import CampusDatetime
from app.schemas.events import Conflict, EventOut

FieldPath = Literal["start_at", "end_at", "resource_id", "expected_attendance"]
Kind = Literal["COMMITMENT", "TASK"]
Title = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Reason = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]


class ChangeFields(BaseModel):
    model_config = ConfigDict(extra="forbid")
    start_at: CampusDatetime | None = None
    end_at: CampusDatetime | None = None
    resource_id: UUID | None = None
    expected_attendance: int | None = Field(default=None, ge=0, strict=True)

    @model_validator(mode="after")
    def validate_changes(self) -> Self:
        if not self.model_fields_set:
            raise ValueError("At least one changed field is required")
        for name in ("start_at", "end_at"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError("Schedule fields cannot be null")
        return self


class ChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)
    changes: ChangeFields


class StageChange(ChangeRequest):
    reason: Reason


class ApplyChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_revision: int = Field(ge=1)


class DependencyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Kind
    title: Title
    field_paths: list[FieldPath] = Field(min_length=1, max_length=4)

    @model_validator(mode="after")
    def unique_fields(self) -> Self:
        if len(set(self.field_paths)) != len(self.field_paths):
            raise ValueError("Dependency bindings must be unique")
        return self


class DependencyOut(BaseModel):
    id: UUID
    event_id: UUID
    kind: Kind
    title: str
    status: str
    needs_revalidation: bool
    reported_by: UUID
    field_paths: list[FieldPath]
    created_at: CampusDatetime
    updated_at: CampusDatetime


class DependencyList(BaseModel):
    items: list[DependencyOut]
    total: int


class ImpactItem(BaseModel):
    dependent_id: UUID
    dependent_kind: Kind
    title: str
    status: str
    changed_fields: list[FieldPath]
    reason: str
    revalidation_required: bool


class ImpactReport(BaseModel):
    event_id: UUID
    base_revision: int
    changed_fields: list[FieldPath]
    evaluated_as: EventStatus
    conflicts: list[Conflict]
    impact: list[ImpactItem]
    advisory: Literal[True] = True


class ChangeProposalOut(BaseModel):
    id: UUID
    event_id: UUID
    base_revision: int
    reason: str
    status: Literal["STAGED", "APPLIED"]
    changes: ChangeFields
    conflicts: list[Conflict]
    impact: list[ImpactItem]
    requested_by: UUID
    created_at: CampusDatetime
    applied_by: UUID | None
    applied_at: CampusDatetime | None


class ChangeProposalList(BaseModel):
    items: list[ChangeProposalOut]
    total: int
    limit: int
    offset: int


class ChangeAppliedOut(BaseModel):
    event: EventOut
    conflicts: list[Conflict]
    impact: list[ImpactItem]
