"""One PostgreSQL transaction behind the write path's ports (spine AD-4, AD-8).

Everything done through a unit of work commits together or not at all. Leaving the block
without calling ``commit`` rolls back, which also releases the campus lock.
"""

from collections.abc import Callable
from dataclasses import dataclass
from types import TracebackType
from typing import Self

from sqlalchemy.orm import Session

from app.repositories.agent_actions import SqlAgentActionStore
from app.repositories.changes import SqlChangeStore
from app.repositories.directory import SqlActorReader, SqlClubReader, SqlResourceReader
from app.repositories.history import SqlAuditWriter, SqlEvidenceWriter, SqlIdempotencyStore
from app.repositories.proposals import SqlProposalStore
from app.repositories.scheduling import (
    SqlEventStore,
    SqlOverrideStore,
    SqlRevisionWriter,
    SqlScheduleLock,
)


@dataclass(frozen=True)
class SqlScheduleWriters:
    lock: SqlScheduleLock
    events: SqlEventStore
    revisions: SqlRevisionWriter
    overrides: SqlOverrideStore


class SqlUnitOfWork:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._session = session_factory()
        events = SqlEventStore(self._session)
        overrides = SqlOverrideStore(self._session)
        self.events = events
        self.clubs = SqlClubReader(self._session)
        self.resources = SqlResourceReader(self._session)
        self.overrides = overrides
        self.actors = SqlActorReader(self._session)
        self.audit = SqlAuditWriter(self._session)
        self.evidence = SqlEvidenceWriter(self._session)
        self.idempotency = SqlIdempotencyStore(self._session)
        self.agent_actions = SqlAgentActionStore(self._session)
        self.proposals = SqlProposalStore(self._session)
        self.changes = SqlChangeStore(self._session)
        self.schedule = SqlScheduleWriters(
            lock=SqlScheduleLock(self._session),
            events=events,
            revisions=SqlRevisionWriter(self._session),
            overrides=overrides,
        )

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        try:
            if self._session.in_transaction():
                self._session.rollback()
        finally:
            self._session.close()

    def commit(self) -> None:
        self._session.commit()
