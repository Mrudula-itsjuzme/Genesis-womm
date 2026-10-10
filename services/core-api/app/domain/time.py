"""Time primitives: aware datetimes, UTC normalisation and an injected clock.

Intervals are half-open ``[start_at, end_at)``. Campus-local conversion to
``Asia/Kolkata`` happens only in API schemas, never here.
"""

from datetime import UTC, datetime
from typing import Protocol


class NaiveDatetimeError(ValueError):
    """A datetime without a UTC offset was supplied."""


class InvalidIntervalError(ValueError):
    """An interval did not satisfy ``start_at < end_at``."""


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    """UTC wall clock for the composed application."""

    def now(self) -> datetime:
        return datetime.now(UTC)  # noqa: TID251 - this adapter is the injected clock source


class FixedClock:
    """Deterministic clock for tests and frozen demo data."""

    def __init__(self, instant: datetime) -> None:
        self._instant = to_utc(instant)

    def now(self) -> datetime:
        return self._instant


def ensure_aware(value: datetime) -> datetime:

    if value.tzinfo is None or value.utcoffset() is None:
        raise NaiveDatetimeError("datetime must carry a UTC offset")
    return value


def to_utc(value: datetime) -> datetime:
    return ensure_aware(value).astimezone(UTC)


def ensure_interval(start_at: datetime, end_at: datetime) -> tuple[datetime, datetime]:
    start, end = to_utc(start_at), to_utc(end_at)
    if not start < end:
        raise InvalidIntervalError("start_at must be strictly before end_at")
    return start, end
