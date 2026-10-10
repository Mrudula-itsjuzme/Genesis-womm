"""What the use cases need from the outside world (spine AD-2, AD-8).

These are the general ports: reading state, writing audit and evidence, and idempotency.
Anything that changes an event's interval, venue or status is deliberately absent; those writes
live in ``schedule_store``, which only ``ScheduleWriteService`` may import (spine AD-4).
"""

from dataclasses import dataclass, replace
from datetime import datetime
from types import TracebackType
from typing import Any, Protocol, Self
from uuid import UUID

from app.domain.authz import Actor
from app.domain.enums import AvailabilityState, EventStatus, OverrideScope
from app.domain.scheduling import Override, ScheduledEvent


@dataclass(frozen=True)
class EventRecord:
    """An event as stored, including its optimistic-lock revision and verification."""

    id: UUID
    club_id: UUID
    title: str
    description: str | None
    start_at: datetime
    end_at: datetime
    resource_id: UUID | None
    expected_attendance: int | None
    audience_tags: tuple[str, ...]
    status: EventStatus
    revision: int
    created_by: UUID
    verified_by: UUID | None
    verified_at: datetime | None
    evidence_id: UUID | None
    is_synthetic: bool
    created_at: datetime
    updated_at: datetime

    def to_scheduled(self) -> ScheduledEvent:
        return ScheduledEvent(
            id=self.id,
            club_id=self.club_id,
            status=self.status,
            start_at=self.start_at,
            end_at=self.end_at,
            resource_id=self.resource_id,
        )

    def but(self, **changes: Any) -> "EventRecord":
        return replace(self, **changes)


@dataclass(frozen=True)
class EvidenceData:
    id: UUID
    kind: str
    reference: str
    issuer: str | None
    captured_at: datetime
    recorded_by: UUID
    created_at: datetime


@dataclass(frozen=True)
class OverrideRecord:
    id: UUID
    scope: OverrideScope
    event_a_id: UUID
    event_b_id: UUID
    reason: str
    authorized_by: UUID
    evidence_id: UUID | None
    created_at: datetime

    def to_domain(self) -> Override:
        return Override(scope=self.scope, event_ids=frozenset({self.event_a_id, self.event_b_id}))


@dataclass(frozen=True)
class AuditRecord:
    id: UUID
    actor_id: UUID | None
    action: str
    entity_type: str
    entity_id: UUID | None
    outcome: str
    reason_code: str | None
    request_id: str
    via: str  # "USER" or "AGENT"
    created_at: datetime


@dataclass(frozen=True)
class StoredResponse:
    request_hash: str
    status_code: int
    response: dict[str, Any]


class IdSource(Protocol):
    def new_id(self) -> UUID: ...


class EventReader(Protocol):
    def get(self, event_id: UUID) -> EventRecord | None: ...

    def list_scheduling_candidates(self) -> list[EventRecord]:
        """Every event that can still hold a time slot: not rejected, cancelled or completed."""
        ...


class ResourceReader(Protocol):
    def availability_of(self, resource_id: UUID | None) -> AvailabilityState:
        """UNKNOWN for no venue or an unknown one. An empty calendar never means free."""
        ...


class OverrideReader(Protocol):
    def for_event(self, event_id: UUID) -> list[OverrideRecord]: ...

    def exists(self, scope: OverrideScope, event_a_id: UUID, event_b_id: UUID) -> bool: ...


class ActorReader(Protocol):
    def load_actor(self, user_id: UUID, *, via_agent: bool = False) -> Actor | None:
        """Build an Actor from database rows, never from anything a client supplied."""
        ...


class AuditWriter(Protocol):
    def add(self, record: AuditRecord) -> None: ...


class EvidenceWriter(Protocol):
    def add(self, evidence: EvidenceData) -> None: ...


class IdempotencyStore(Protocol):
    def get(self, actor_id: UUID, key: str) -> StoredResponse | None: ...

    def put(
        self, actor_id: UUID, key: str, stored: StoredResponse, created_at: datetime
    ) -> None: ...


class UnitOfWork(Protocol):
    """One transaction. Leaving the block without ``commit`` rolls everything back."""

    events: EventReader
    resources: ResourceReader
    overrides: OverrideReader
    actors: ActorReader
    audit: AuditWriter
    evidence: EvidenceWriter
    idempotency: IdempotencyStore

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...
