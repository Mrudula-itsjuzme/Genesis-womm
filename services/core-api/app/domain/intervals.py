"""Half-open intervals and the campus-wide gap rule (spine AD-5, AD-17).

Intervals are ``[start, end)``: two events that merely touch do not overlap. The gap rule is
a CampusCue planning assumption, not verified university policy: two events are acceptable
when one ends at least ``gap`` before the other starts.

Everything is normalised to UTC first. ``datetime + timedelta`` on a zone-aware value is
wall-clock arithmetic, which is wrong across DST changes; UTC has none.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.domain.time import ensure_interval


@dataclass(frozen=True)
class Interval:
    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        start, end = ensure_interval(self.start, self.end)
        object.__setattr__(self, "start", start)
        object.__setattr__(self, "end", end)


def _require_positive(gap: timedelta) -> None:
    if gap <= timedelta(0):
        raise ValueError("gap must be a positive duration")


def overlaps(a: Interval, b: Interval) -> bool:
    return a.start < b.end and b.start < a.end


def shared_interval(a: Interval, b: Interval) -> Interval | None:
    """The time both intervals cover, or None when they only touch or are apart."""
    if not overlaps(a, b):
        return None
    return Interval(max(a.start, b.start), min(a.end, b.end))


def gap_violated(a: Interval, b: Interval, gap: timedelta) -> bool:
    """True unless ``a.end + gap <= b.start`` or ``b.end + gap <= a.start``.

    Overlapping intervals always violate the gap. Exactly ``gap`` apart passes; one minute
    less fails.
    """
    _require_positive(gap)
    return not (a.end + gap <= b.start or b.end + gap <= a.start)


def buffer_window(a: Interval, b: Interval, gap: timedelta) -> Interval:
    """The protected buffer after the event that ends first: ``[end, end + gap)``.

    Meaningful for events that do not overlap; the second starts inside this window when the
    gap is violated.
    """
    _require_positive(gap)
    first = a if (a.end, a.start) <= (b.end, b.start) else b
    return Interval(first.end, first.end + gap)
