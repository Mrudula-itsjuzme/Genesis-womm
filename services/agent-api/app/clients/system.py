"""The real clock, for the composition root. Orchestration only ever sees the `Clock` port."""

from datetime import UTC, datetime


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)
