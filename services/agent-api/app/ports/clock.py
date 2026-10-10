from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    def now(self) -> datetime: ...


class FixedClock:
    """Deterministic clock for tests and frozen demos."""

    def __init__(self, instant: datetime) -> None:
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("FixedClock needs an offset-aware datetime")
        self._instant = instant.astimezone(UTC)

    def now(self) -> datetime:
        return self._instant
