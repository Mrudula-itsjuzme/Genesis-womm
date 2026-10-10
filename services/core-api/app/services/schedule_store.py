"""The only writers of an event's interval, venue and status (spine AD-4).

Import-linter allows exactly one service to import this module, ``schedule_write``, plus the
SQL adapter that implements it. A service that holds a plain ``UnitOfWork`` cannot reach these
methods, so nothing can write an event around the conflict engine or the campus lock.
"""

from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.services.ports import EventRecord, OverrideRecord, UnitOfWork


class EventWriter(Protocol):
    def insert(self, record: EventRecord) -> None: ...

    def update(self, record: EventRecord, *, expected_revision: int) -> None:
        """Replace the stored event only if it is still at ``expected_revision``.

        Raises ``StaleRevisionError`` and changes nothing otherwise.
        """
        ...


class RevisionWriter(Protocol):
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
    ) -> None: ...


class OverrideWriter(Protocol):
    def add(self, record: OverrideRecord) -> None: ...


class ScheduleLock(Protocol):
    def acquire(self) -> None:
        """Take the campus-wide schedule lock for the rest of this transaction.

        Everything that can change what the conflict engine reports must call this before it
        reads. The lock is released automatically at commit or rollback.
        """
        ...


class ScheduleWriters(Protocol):
    lock: ScheduleLock
    events: EventWriter
    revisions: RevisionWriter
    overrides: OverrideWriter


class ScheduleUnitOfWork(UnitOfWork, Protocol):
    schedule: ScheduleWriters
