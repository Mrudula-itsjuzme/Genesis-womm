"""What the use cases need from the outside world (spine AD-2, AD-8).

These are the general ports: reading state, writing audit and evidence, and idempotency.
Anything that changes an event's interval, venue or status is deliberately absent; those writes
live in ``schedule_store``, which only ``ScheduleWriteService`` may import (spine AD-4).
"""

from dataclasses import dataclass, replace
from datetime import datetime
from types import TracebackType
from typing import Any, Literal, Protocol, Self
from uuid import UUID

from app.domain.authz import Actor
from app.domain.enums import (
    AgentActionStatus,
    AgentActionType,
    AvailabilityState,
    EventStatus,
    FreshnessState,
    OverrideScope,
    ResourceKind,
    Role,
)
from app.domain.scheduling import Conflict, Override, ScheduledEvent


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
class ResourceRecord:
    id: UUID
    kind: ResourceKind
    name: str
    description: str | None
    location: str | None
    capacity: int | None
    availability_state: AvailabilityState
    freshness_state: FreshnessState
    source_id: str
    source_url: str | None
    collected_at: datetime | None
    last_checked_at: datetime | None
    is_synthetic: bool


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
class AgentActionRecord:
    """A proposal the Agent filed for ``requested_by`` to confirm (spine AD-9)."""

    id: UUID
    type: AgentActionType
    status: AgentActionStatus
    summary: str
    requested_by: UUID
    club_id: UUID
    target_event_id: UUID | None
    expected_revision: int | None
    payload: dict[str, Any]
    conflicts: tuple[Conflict, ...]  # the dry run stored when the proposal was filed
    decided_by: UUID | None
    decided_at: datetime | None
    result_entity_type: str | None
    result_entity_id: UUID | None
    created_at: datetime
    updated_at: datetime

    def but(self, **changes: Any) -> "AgentActionRecord":
        return replace(self, **changes)


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


class TokenService(Protocol):
    def issue(self, user_id: UUID) -> tuple[str, datetime]: ...

    def verify(self, token: str) -> UUID: ...


class DelegationTokenService(Protocol):
    def issue(self, user_id: UUID, request_id: str) -> tuple[str, datetime]: ...

    def verify(self, token: str) -> UUID: ...


@dataclass(frozen=True)
class MembershipIdentity:
    """A membership that may be safely returned in a signed-in user's profile."""

    club_id: UUID
    club_name: str
    role: Role


@dataclass(frozen=True)
class UserIdentity:
    """Directory data for a known user, loaded only from the authoritative store."""

    id: UUID
    email: str
    display_name: str
    campus_admin: bool
    memberships: tuple[MembershipIdentity, ...]
    is_synthetic: bool


class EventReader(Protocol):
    def get(self, event_id: UUID) -> EventRecord | None: ...

    def list_events(
        self,
        *,
        club_id: UUID | None,
        status: EventStatus | None,
        resource_id: UUID | None,
        starts_after: datetime | None,
        starts_before: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[EventRecord], int]: ...

    def list_scheduling_candidates(
        self, *, starts_before: datetime, ends_after: datetime
    ) -> list[EventRecord]:
        """Events that could conflict with a window: those that start before ``starts_before``
        and end after ``ends_after``, excluding rejected, cancelled and completed ones.

        The caller passes its interval widened by the campus gap on both sides. An event outside
        that window overlaps nothing and is at least the gap away, so it cannot produce a
        conflict, and leaving it out never changes the engine's answer.
        """
        ...


class ResourceReader(Protocol):
    def availability_of(self, resource_id: UUID) -> AvailabilityState | None:
        """The venue's evidence-backed state, or None if there is no such resource.

        A venue starts UNKNOWN. An empty calendar never means it is free.
        """
        ...

    def get(self, resource_id: UUID) -> ResourceRecord | None: ...

    def list_resources(
        self, *, kind: ResourceKind | None, query: str | None, limit: int, offset: int
    ) -> tuple[list[ResourceRecord], int]: ...


class ClubReader(Protocol):
    def exists(self, club_id: UUID) -> bool: ...


class OverrideReader(Protocol):
    def for_event(self, event_id: UUID) -> list[OverrideRecord]: ...

    def exists(self, scope: OverrideScope, event_a_id: UUID, event_b_id: UUID) -> bool: ...


class ActorReader(Protocol):
    def load_actor(self, user_id: UUID, *, via_agent: bool = False) -> Actor | None:
        """Build an Actor from database rows, never from anything a client supplied."""
        ...

    def load_identity(self, user_id: UUID) -> UserIdentity | None:
        """Return a user's profile and memberships from database rows."""
        ...

    def load_identity_by_email(self, email: str) -> UserIdentity | None:
        """Return a user's profile and memberships by their stored email address."""
        ...


class DirectoryUnitOfWork(Protocol):
    """The short read-only transaction used to resolve a user session."""

    @property
    def actors(self) -> ActorReader: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...


class AgentActionStore(Protocol):
    def get(self, action_id: UUID) -> AgentActionRecord | None: ...

    def list_for(
        self,
        requested_by: UUID,
        *,
        status: AgentActionStatus | None,
        event_id: UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[AgentActionRecord], int]:
        """One person's proposals, newest first, with the total that matched."""
        ...

    def add(self, record: AgentActionRecord) -> None: ...

    def decide(
        self,
        action_id: UUID,
        *,
        status: AgentActionStatus,
        decided_by: UUID,
        decided_at: datetime,
        result_entity_type: str | None,
        result_entity_id: UUID | None,
    ) -> bool:
        """Move a PROPOSED action to its decision. False when it was no longer PROPOSED.

        This is a compare-and-set in one statement, so two people (or two retries) deciding
        the same proposal at once cannot both win.
        """
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

    # Read-only members, so an adapter may expose a more specific type than the port names.
    @property
    def events(self) -> EventReader: ...

    @property
    def clubs(self) -> ClubReader: ...

    @property
    def resources(self) -> ResourceReader: ...

    @property
    def overrides(self) -> OverrideReader: ...

    @property
    def actors(self) -> ActorReader: ...

    @property
    def audit(self) -> AuditWriter: ...

    @property
    def evidence(self) -> EvidenceWriter: ...

    @property
    def idempotency(self) -> IdempotencyStore: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...


class AgentActionUnitOfWork(Protocol):
    """One transaction for filing, listing, confirming and rejecting proposals."""

    @property
    def agent_actions(self) -> AgentActionStore: ...

    @property
    def events(self) -> EventReader: ...

    @property
    def clubs(self) -> ClubReader: ...

    @property
    def audit(self) -> AuditWriter: ...

    @property
    def idempotency(self) -> IdempotencyStore: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...


@dataclass(frozen=True)
class ChatTurn:
    """What a person said to the planning assistant: bounded history, newest last."""

    messages: tuple[tuple[Literal["user", "assistant"], str], ...]
    event_id: UUID | None = None


class AgentGateway(Protocol):
    def chat(self, turn: ChatTurn, *, delegation_token: str, request_id: str) -> dict[str, Any]:
        """Relay one turn to the Agent and return its reply as decoded JSON.

        Raises ``AgentUnavailableError`` when it cannot be reached or does not answer in time,
        and ``AgentOutputInvalidError`` when it answers with something that is not a reply.
        """
        ...
