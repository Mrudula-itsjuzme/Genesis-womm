"""Readiness: is this service able to do its own job? (spine AD-19)

Core is ready when its database answers and the applied migration head matches the code.
Agent, RAG and the LLM are optional and never affect readiness, so a down model cannot make
deterministic scheduling look unavailable.
"""

from dataclasses import dataclass
from typing import Protocol


class ReadinessProbe(Protocol):
    """Port implemented by the database adapter."""

    def database_reachable(self) -> bool: ...

    def applied_migration(self) -> str | None: ...


@dataclass(frozen=True)
class ReadinessReport:
    ready: bool
    checks: dict[str, bool]
    migration_head: str | None
    expected_head: str


class ReadinessService:
    def __init__(self, probe: ReadinessProbe, expected_head: str) -> None:
        self._probe = probe
        self._expected_head = expected_head

    def check(self) -> ReadinessReport:
        database = self._probe.database_reachable()
        applied = self._probe.applied_migration() if database else None
        migrations = database and applied == self._expected_head
        return ReadinessReport(
            ready=database and migrations,
            checks={"database": database, "migrations": migrations},
            migration_head=applied,
            expected_head=self._expected_head,
        )
