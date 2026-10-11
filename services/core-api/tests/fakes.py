"""Deterministic fakes for Core's outbound ports (spine AD-2)."""

from typing import Any

from pydantic import SecretStr

from app.settings import Settings


def make_settings(**overrides: Any) -> Settings:
    """Hermetic settings: never reads the developer's .env or real secrets."""
    values: dict[str, Any] = {
        "session_signing_key": SecretStr("s" * 40),
        "delegation_signing_key": SecretStr("d" * 40),
        "internal_api_key": SecretStr("i" * 40),
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


class FakeReadinessProbe:
    """Stands in for the database; counts calls so tests can assert what was skipped."""

    def __init__(self, *, reachable: bool = True, applied: str | None = "0001") -> None:
        self._reachable = reachable
        self._applied = applied
        self.applied_calls = 0

    def database_reachable(self) -> bool:
        return self._reachable

    def applied_migration(self) -> str | None:
        self.applied_calls += 1
        return self._applied


# ---- an in-memory database for the write path --------------------------------------------

import copy  # noqa: E402
from dataclasses import dataclass, field, replace  # noqa: E402
from datetime import datetime  # noqa: E402
from types import TracebackType  # noqa: E402
from typing import Self  # noqa: E402
from uuid import UUID  # noqa: E402

from app.domain.authz import Actor  # noqa: E402
from app.domain.enums import (  # noqa: E402
    AgentActionStatus,
    AvailabilityState,
    EventStatus,
    OverrideScope,
    ProposalStatus,
)
from app.services.errors import StaleRevisionError  # noqa: E402
from app.services.ports import (  # noqa: E402
    AgentActionRecord,
    AuditRecord,
    EventRecord,
    EvidenceData,
    OverrideRecord,
    ProposalRecord,
    ResourceRecord,
    StoredResponse,
    UserIdentity,
)

INACTIVE = {EventStatus.REJECTED, EventStatus.CANCELLED, EventStatus.COMPLETED}


class SequentialIds:
    """Deterministic ids: UUID(int=1000), UUID(int=1001), ..."""

    def __init__(self, start: int = 1000) -> None:
        self._next = start

    def new_id(self) -> UUID:
        value = UUID(int=self._next)
        self._next += 1
        return value


@dataclass
class RevisionRow:
    revision_id: UUID
    event_id: UUID
    revision: int
    previous: dict[str, Any] | None
    current: dict[str, Any]
    actor_id: UUID
    reason: str | None
    created_at: datetime


@dataclass
class State:
    actors: dict[UUID, Actor] = field(default_factory=dict)
    clubs: set[UUID] = field(default_factory=set)
    resources: dict[UUID, AvailabilityState] = field(default_factory=dict)
    events: dict[UUID, EventRecord] = field(default_factory=dict)
    overrides: list[OverrideRecord] = field(default_factory=list)
    evidence: dict[UUID, EvidenceData] = field(default_factory=dict)
    revisions: list[RevisionRow] = field(default_factory=list)
    audit: list[AuditRecord] = field(default_factory=list)
    keys: dict[tuple[UUID, str], StoredResponse] = field(default_factory=dict)
    agent_actions: dict[UUID, AgentActionRecord] = field(default_factory=dict)
    proposals: dict[UUID, ProposalRecord] = field(default_factory=dict)

    def copy(self) -> "State":
        # Records are frozen, so copying the containers is enough.
        return State(**{name: copy.copy(value) for name, value in vars(self).items()})


class InMemoryDatabase:
    """Committed state plus a call log, so tests can assert what happened and in what order."""

    def __init__(self) -> None:
        self.state = State()
        self.log: list[str] = []
        self.fail_at: str | None = None
        self.commits = 0

    def uow(self) -> "FakeUnitOfWork":
        return FakeUnitOfWork(self)

    def fail_if(self, step: str) -> None:
        if self.fail_at == step:
            raise RuntimeError(f"injected failure at {step}")


class _Events:
    """Reader and writer in one: the real adapter splits them across two ports."""

    def __init__(self, db: InMemoryDatabase, work: State) -> None:
        self._db, self._work = db, work

    def get(self, event_id: UUID) -> EventRecord | None:
        self._db.log.append("read:event")
        return self._work.events.get(event_id)

    def list_events(
        self,
        *,
        club_id: UUID | None,
        status: EventStatus | None,
        resource_id: UUID | None,
        starts_after: datetime | None,
        starts_before: datetime | None,
        draft_clubs: frozenset[UUID] | None,
        limit: int,
        offset: int,
    ) -> tuple[list[EventRecord], int]:
        records = [
            event
            for event in self._work.events.values()
            if (
                (
                    draft_clubs is None
                    or event.status is not EventStatus.DRAFT
                    or event.club_id in draft_clubs
                )
                and (club_id is None or event.club_id == club_id)
                and (status is None or event.status is status)
                and (resource_id is None or event.resource_id == resource_id)
                and (starts_after is None or event.start_at >= starts_after)
                and (starts_before is None or event.start_at < starts_before)
            )
        ]
        records.sort(key=lambda event: (event.start_at, event.id))
        return records[offset : offset + limit], len(records)

    def list_scheduling_candidates(
        self, *, starts_before: datetime, ends_after: datetime
    ) -> list[EventRecord]:
        self._db.log.append("read:candidates")
        return [
            e
            for e in self._work.events.values()
            if e.status not in INACTIVE and e.start_at < starts_before and e.end_at > ends_after
        ]

    def insert(self, record: EventRecord) -> None:
        self._db.fail_if("events.insert")
        self._db.log.append("write:event.insert")
        self._work.events[record.id] = record

    def update(self, record: EventRecord, *, expected_revision: int) -> None:
        self._db.fail_if("events.update")
        self._db.log.append("write:event.update")
        stored = self._work.events.get(record.id)
        if stored is None or stored.revision != expected_revision:
            raise StaleRevisionError(
                record.id, expected_revision, None if stored is None else stored.revision
            )
        self._work.events[record.id] = record


class _Clubs:
    def __init__(self, work: State) -> None:
        self._work = work

    def exists(self, club_id: UUID) -> bool:
        return club_id in self._work.clubs


class _Resources:
    def __init__(self, work: State) -> None:
        self._work = work

    def availability_of(self, resource_id: UUID) -> AvailabilityState | None:
        return self._work.resources.get(resource_id)

    def availability_of_many(self, resource_ids: set[UUID]) -> dict[UUID, AvailabilityState]:
        return {
            resource_id: availability
            for resource_id in resource_ids
            if (availability := self._work.resources.get(resource_id)) is not None
        }

    def get(self, resource_id: UUID) -> ResourceRecord | None:
        return None

    def list_resources(self, **_: Any) -> tuple[list[ResourceRecord], int]:
        return [], 0


class _Overrides:
    def __init__(self, db: InMemoryDatabase, work: State) -> None:
        self._db, self._work = db, work

    def for_event(self, event_id: UUID) -> list[OverrideRecord]:
        self._db.log.append("read:overrides")
        return [o for o in self._work.overrides if event_id in (o.event_a_id, o.event_b_id)]

    def exists(self, scope: OverrideScope, event_a_id: UUID, event_b_id: UUID) -> bool:
        return any(
            o.scope is scope and (o.event_a_id, o.event_b_id) == (event_a_id, event_b_id)
            for o in self._work.overrides
        )

    def add(self, record: OverrideRecord) -> None:
        self._db.fail_if("overrides.add")
        self._db.log.append("write:override")
        self._work.overrides.append(record)


class _Actors:
    def __init__(self, work: State) -> None:
        self._work = work

    def load_actor(self, user_id: UUID, *, via_agent: bool = False) -> Actor | None:
        actor = self._work.actors.get(user_id)
        return (
            None
            if actor is None
            else Actor(
                user_id=actor.user_id,
                campus_admin=actor.campus_admin,
                memberships=actor.memberships,
                via_agent=via_agent,
            )
        )

    def load_identity(self, user_id: UUID) -> UserIdentity | None:
        return None

    def load_identity_by_email(self, email: str) -> UserIdentity | None:
        return None


class _Audit:
    def __init__(self, db: InMemoryDatabase, work: State) -> None:
        self._db, self._work = db, work

    def add(self, record: AuditRecord) -> None:
        self._db.fail_if("audit.add")
        self._db.log.append("write:audit")
        self._work.audit.append(record)


class _Evidence:
    def __init__(self, db: InMemoryDatabase, work: State) -> None:
        self._db, self._work = db, work

    def add(self, evidence: EvidenceData) -> None:
        self._db.fail_if("evidence.add")
        self._db.log.append("write:evidence")
        self._work.evidence[evidence.id] = evidence


class _Idempotency:
    def __init__(self, db: InMemoryDatabase, work: State) -> None:
        self._db, self._work = db, work

    def get(self, actor_id: UUID, key: str) -> StoredResponse | None:
        self._db.log.append("read:idempotency")
        return self._work.keys.get((actor_id, key))

    def put(self, actor_id: UUID, key: str, stored: StoredResponse, created_at: datetime) -> None:
        self._db.log.append("write:idempotency")
        self._work.keys[(actor_id, key)] = stored


class _AgentActions:
    """The in-memory twin of ``SqlAgentActionStore``, including the one-shot decision."""

    def __init__(self, db: InMemoryDatabase, work: State) -> None:
        self._db, self._work = db, work

    def get(self, action_id: UUID) -> AgentActionRecord | None:
        self._db.log.append("read:agent_action")
        return self._work.agent_actions.get(action_id)

    def list_for(
        self,
        requested_by: UUID,
        *,
        status: AgentActionStatus | None,
        event_id: UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[AgentActionRecord], int]:
        self._db.log.append("read:agent_actions")
        matching = [
            record
            for record in self._work.agent_actions.values()
            if record.requested_by == requested_by
            and (status is None or record.status is status)
            and (event_id is None or record.target_event_id == event_id)
        ]
        matching.sort(key=lambda r: (r.created_at, r.id), reverse=True)
        return matching[offset : offset + limit], len(matching)

    def add(self, record: AgentActionRecord) -> None:
        self._db.fail_if("agent_actions.add")
        self._db.log.append("write:agent_action")
        self._work.agent_actions[record.id] = record

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
        self._db.fail_if("agent_actions.decide")
        record = self._work.agent_actions.get(action_id)
        if record is None or record.status is not AgentActionStatus.PROPOSED:
            return False
        self._db.log.append("write:agent_action_decision")
        self._work.agent_actions[action_id] = record.but(
            status=status,
            decided_by=decided_by,
            decided_at=decided_at,
            result_entity_type=result_entity_type,
            result_entity_id=result_entity_id,
            updated_at=decided_at,
        )
        return True


class _Proposals:
    """The in-memory twin of ``SqlProposalStore``. Records are mutable, so it copies them in and
    out; otherwise a rolled-back transaction could leak edits into committed state."""

    def __init__(self, db: InMemoryDatabase, work: State) -> None:
        self._db, self._work = db, work

    def get(self, proposal_id: UUID) -> ProposalRecord | None:
        self._db.log.append("read:proposal")
        stored = self._work.proposals.get(proposal_id)
        return None if stored is None else replace(stored)

    def add(self, record: ProposalRecord) -> None:
        self._db.fail_if("proposals.add")
        self._db.log.append("write:proposal")
        self._work.proposals[record.id] = replace(record)

    def next_revision(self, event_id: UUID) -> int:
        revisions = [p.revision for p in self._work.proposals.values() if p.event_id == event_id]
        return max(revisions, default=0) + 1

    def save(self, record: ProposalRecord, *, expected_status: ProposalStatus) -> bool:
        self._db.fail_if("proposals.save")
        # Like ``UPDATE ... WHERE status = :expected`` under READ COMMITTED, the comparison sees
        # what other transactions have committed, not this transaction's snapshot.
        committed = self._db.state.proposals.get(record.id)
        current = self._work.proposals.get(record.id)
        if committed is None or committed.status is not expected_status or current is None:
            return False
        self._db.log.append("write:proposal_review")
        self._work.proposals[record.id] = replace(
            current,
            status=record.status,
            reviewed_by=record.reviewed_by,
            reviewed_at=record.reviewed_at,
            review_note=record.review_note,
            rag_ingested_at=record.rag_ingested_at,
            rag_deleted_at=record.rag_deleted_at,
        )
        return True


class _Revisions:
    def __init__(self, db: InMemoryDatabase, work: State) -> None:
        self._db, self._work = db, work

    def add(
        self,
        *,
        revision_id: UUID,
        event_id: UUID,
        revision: int,
        previous: dict[str, Any] | None,
        current: dict[str, Any],
        actor_id: UUID,
        reason: str | None,
        created_at: datetime,
    ) -> None:
        self._db.log.append("write:revision")
        self._work.revisions.append(
            RevisionRow(
                revision_id, event_id, revision, previous, current, actor_id, reason, created_at
            )
        )


class _Lock:
    def __init__(self, db: InMemoryDatabase) -> None:
        self._db = db

    def acquire(self) -> None:
        self._db.log.append("lock")


class _ScheduleWriters:
    def __init__(self, db: InMemoryDatabase, work: State, events: _Events) -> None:
        self.lock = _Lock(db)
        self.events = events
        self.revisions = _Revisions(db, work)
        self.overrides = _Overrides(db, work)


class FakeUnitOfWork:
    """Works on a copy of the database and applies it only on ``commit``."""

    def __init__(self, db: InMemoryDatabase) -> None:
        self._db = db
        self._work = db.state.copy()
        events = _Events(db, self._work)
        self.events = events
        self.clubs = _Clubs(self._work)
        self.resources = _Resources(self._work)
        self.overrides = _Overrides(db, self._work)
        self.actors = _Actors(self._work)
        self.audit = _Audit(db, self._work)
        self.evidence = _Evidence(db, self._work)
        self.idempotency = _Idempotency(db, self._work)
        self.agent_actions = _AgentActions(db, self._work)
        self.proposals = _Proposals(db, self._work)
        self.schedule = _ScheduleWriters(db, self._work, events)

    def __enter__(self) -> Self:
        self._db.log.append("begin")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._work is not self._db.state:
            self._db.log.append("rollback")

    def commit(self) -> None:
        self._db.state = self._work
        self._db.commits += 1
        self._db.log.append("commit")
