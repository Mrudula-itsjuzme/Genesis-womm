from datetime import date, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.domain.enums import AvailabilityState, FreshnessState, ResourceKind
from app.schemas.common import CampusDatetime


class ResourceOut(BaseModel):
    """A sourced campus resource. Provenance travels with it; availability is never inferred."""

    id: UUID
    kind: ResourceKind
    name: str
    description: str | None
    location: str | None
    capacity: int | None
    availability_state: AvailabilityState = Field(
        description="UNKNOWN by default. An empty calendar never means the resource is free."
    )
    freshness_state: FreshnessState
    source_id: str
    source_url: str | None
    collected_at: CampusDatetime | None
    last_checked_at: CampusDatetime | None
    synthetic: bool = Field(description="True for seeded demo data.")


class ResourceList(BaseModel):
    items: list[ResourceOut]
    limit: int
    offset: int
    total: int


ResourceInterestCategory = Literal[
    "HPC / GPU compute",
    "Computer lab",
    "AV / recording kit",
    "Workshop equipment",
    "Other shared resource",
    "Er kit",
    "Bio signal",
    "Eeg kit",
    "Hardware sensors and kit",
    "Power extensions",
    "Wifi support",
    "Lab suport",
    "3d printing",
    "Vlsi boards",
]


class ResourceInterestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: ResourceInterestCategory
    purpose: str = Field(min_length=1, max_length=160)
    preferred_date: date
    start_time: time
    end_time: time
    requirements: str | None = Field(default=None, max_length=400)

    @field_validator("purpose")
    @classmethod
    def valid_purpose(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("purpose must not be blank")
        return cleaned

    @field_validator("requirements")
    @classmethod
    def clean_requirements(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @field_validator("end_time")
    @classmethod
    def valid_end_time(cls, value: time, info: ValidationInfo) -> time:
        start_time = info.data.get("start_time")
        if isinstance(start_time, time) and value <= start_time:
            raise ValueError("end_time must be later than start_time")
        return value


class ResourceInterestOut(BaseModel):
    id: UUID
    requester_id: UUID
    category: str
    purpose: str
    preferred_date: date
    start_time: time
    end_time: time
    requirements: str | None
    created_at: CampusDatetime
