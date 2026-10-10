"""PostgreSQL adapters for events, their history and the campus lock (spine AD-4, AD-8, AD-20).

These implement the ports in ``services.ports`` and ``services.schedule_store``. Only
``ScheduleWriteService`` is allowed to reach the write side.
"""

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select, text, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.domain.enums import EventStatus, OverrideScope
from app.models.scheduling import Event, EventRevision, ScheduleOverride
from app.services.errors import StaleRevisionError
from app.services.ports import EventRecord, OverrideRecord

# One campus-wide key for pg_advisory_xact_lock. Every write that can change what the conflict
# engine reports takes it first, so the check and the write cannot interleave across sessions.
CAMPUS_SCHEDULE_LOCK_KEY = 0x4341_4D50_5553_0001

_INACTIVE = [
    status.value for status in (EventStatus.REJECTED, EventStatus.CANCELLED, EventStatus.COMPLETED)
]


def _to_record(row: Event) -> EventRecord:
    return EventRecord(
        id=row.id,
        club_id=row.club_id,
        title=row.title,
        description=row.description,
        start_at=row.start_at,
        end_at=row.end_at,
        resource_id=row.resource_id,
        expected_attendance=row.expected_attendance,
        audience_tags=tuple(row.audience_tags),
        status=EventStatus(row.status),
        revision=row.revision,
        created_by=row.created_by,
        verified_by=row.verified_by,
        verified_at=row.verified_at,
        evidence_id=row.evidence_id,
        is_synthetic=row.is_synthetic,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _columns(record: EventRecord) -> dict[str, Any]:
    return {
        "club_id": record.club_id,
        "title": record.title,
        "description": record.description,
        "start_at": record.start_at,
        "end_at": record.end_at,
        "resource_id": record.resource_id,
        "expected_attendance": record.expected_attendance,
        "audience_tags": list(record.audience_tags),
        "status": record.status.value,
        "revision": record.revision,
        "created_by": record.created_by,
        "verified_by": record.verified_by,
        "verified_at": record.verified_at,
        "evidence_id": record.evidence_id,
        "is_synthetic": record.is_synthetic,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
    }


class SqlEventStore:
    """Reads and writes events. One object serves both the reader and the writer port."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, event_id: UUID) -> EventRecord | None:
        row = self._session.get(Event, event_id, populate_existing=True)
        return None if row is None else _to_record(row)

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
    ) -> tuple[list[EventRecord], int]:
        filters = []
        if club_id is not None:
            filters.append(Event.club_id == club_id)
        if status is not None:
            filters.append(Event.status == status.value)
        if resource_id is not None:
            filters.append(Event.resource_id == resource_id)
        if starts_after is not None:
            filters.append(Event.start_at >= starts_after)
        if starts_before is not None:
            filters.append(Event.start_at < starts_before)
        statement = select(Event).where(*filters).order_by(Event.start_at, Event.id)
        total = int(
            self._session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        )
        rows = self._session.scalars(statement.limit(limit).offset(offset)).all()
        return [_to_record(row) for row in rows], total

    def list_scheduling_candidates(
        self, *, starts_before: datetime, ends_after: datetime
    ) -> list[EventRecord]:
        statement = (
            select(Event)
            .where(
                Event.status.not_in(_INACTIVE),
                Event.start_at < starts_before,
                Event.end_at > ends_after,
            )
            .order_by(Event.start_at, Event.id)
            .execution_options(populate_existing=True)
        )
        return [_to_record(row) for row in self._session.scalars(statement)]

    def insert(self, record: EventRecord) -> None:
        self._session.add(Event(id=record.id, **_columns(record)))
        self._session.flush()

    def update(self, record: EventRecord, *, expected_revision: int) -> None:
        # Who created an event, for which club, and when, never changes.
        immutable = {"created_by", "created_at", "club_id", "is_synthetic"}
        columns = {k: v for k, v in _columns(record).items() if k not in immutable}
        result = cast(
            "CursorResult[Any]",
            self._session.execute(
                update(Event)
                .where(Event.id == record.id, Event.revision == expected_revision)
                .values(**columns)
            ),
        )
        if result.rowcount != 1:
            actual = self._session.scalar(select(Event.revision).where(Event.id == record.id))
            raise StaleRevisionError(record.id, expected_revision, actual)
        # The UPDATE bypassed the identity map; drop any copy of this row it may be holding.
        self._session.expire_all()


class SqlRevisionWriter:
    def __init__(self, session: Session) -> None:
        self._session = session

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
        self._session.add(
            EventRevision(
                id=revision_id,
                event_id=event_id,
                revision=revision,
                previous=previous,
                current=current,
                actor_id=actor_id,
                reason=reason,
                created_at=created_at,
            )
        )
        self._session.flush()


class SqlOverrideStore:
    """Reads and writes overrides. Pairs are stored in canonical order (a < b)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    @staticmethod
    def _to_record(row: ScheduleOverride) -> OverrideRecord:
        return OverrideRecord(
            id=row.id,
            scope=OverrideScope(row.scope),
            event_a_id=row.event_a_id,
            event_b_id=row.event_b_id,
            reason=row.reason,
            authorized_by=row.authorized_by,
            evidence_id=row.evidence_id,
            created_at=row.created_at,
        )

    def for_event(self, event_id: UUID) -> list[OverrideRecord]:
        statement = (
            select(ScheduleOverride)
            .where(
                (ScheduleOverride.event_a_id == event_id)
                | (ScheduleOverride.event_b_id == event_id)
            )
            .order_by(ScheduleOverride.created_at, ScheduleOverride.id)
        )
        return [self._to_record(row) for row in self._session.scalars(statement)]

    def exists(self, scope: OverrideScope, event_a_id: UUID, event_b_id: UUID) -> bool:
        found = self._session.scalar(
            select(ScheduleOverride.id).where(
                ScheduleOverride.scope == scope.value,
                ScheduleOverride.event_a_id == event_a_id,
                ScheduleOverride.event_b_id == event_b_id,
            )
        )
        return found is not None

    def add(self, record: OverrideRecord) -> None:
        self._session.add(
            ScheduleOverride(
                id=record.id,
                scope=record.scope.value,
                event_a_id=record.event_a_id,
                event_b_id=record.event_b_id,
                reason=record.reason,
                authorized_by=record.authorized_by,
                evidence_id=record.evidence_id,
                created_at=record.created_at,
            )
        )
        self._session.flush()


class SqlScheduleLock:
    def __init__(self, session: Session) -> None:
        self._session = session

    def acquire(self) -> None:
        """Block until the campus lock is ours; it is released at commit or rollback."""
        self._session.execute(
            text("SELECT pg_advisory_xact_lock(:key)"), {"key": CAMPUS_SCHEDULE_LOCK_KEY}
        )
