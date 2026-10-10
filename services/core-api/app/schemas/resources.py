from uuid import UUID

from pydantic import BaseModel, Field

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
