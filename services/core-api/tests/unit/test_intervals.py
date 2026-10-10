from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.domain.intervals import (
    Interval,
    buffer_window,
    gap_violated,
    overlaps,
    shared_interval,
)
from app.domain.time import InvalidIntervalError, NaiveDatetimeError

GAP = timedelta(minutes=120)
DAY = datetime(2026, 10, 20, tzinfo=UTC)


def at(hour: int, minute: int = 0) -> datetime:
    return DAY.replace(hour=hour, minute=minute)


def span(start: tuple[int, int], end: tuple[int, int]) -> Interval:
    return Interval(at(*start), at(*end))


def test_an_interval_must_have_a_start_strictly_before_its_end() -> None:
    with pytest.raises(InvalidIntervalError):
        Interval(at(9), at(9))
    with pytest.raises(InvalidIntervalError):
        Interval(at(10), at(9))


def test_an_interval_rejects_naive_datetimes() -> None:
    with pytest.raises(NaiveDatetimeError):
        Interval(datetime(2026, 10, 20, 9), at(10))


def test_an_interval_is_normalised_to_utc() -> None:
    ist = timezone(timedelta(hours=5, minutes=30))
    interval = Interval(
        datetime(2026, 10, 20, 9, 0, tzinfo=ist), datetime(2026, 10, 20, 11, tzinfo=ist)
    )
    assert interval.start == datetime(2026, 10, 20, 3, 30, tzinfo=UTC)
    assert interval.start.utcoffset() == timedelta(0)


@pytest.mark.parametrize(
    ("a", "b", "expected"),
    [
        (((9, 0), (12, 0)), ((10, 0), (11, 0)), True),  # containment
        (((9, 0), (11, 0)), ((10, 0), (12, 0)), True),  # partial overlap
        (((9, 0), (11, 0)), ((9, 0), (11, 0)), True),  # identical
        (((9, 0), (11, 0)), ((10, 59), (12, 0)), True),  # one minute of overlap
        (((9, 0), (11, 0)), ((11, 0), (12, 0)), False),  # touching: half-open, no overlap
        (((9, 0), (11, 0)), ((12, 0), (13, 0)), False),  # disjoint
    ],
)
def test_overlap_is_half_open_and_symmetric(
    a: tuple[tuple[int, int], tuple[int, int]],
    b: tuple[tuple[int, int], tuple[int, int]],
    expected: bool,
) -> None:
    first, second = span(*a), span(*b)
    assert overlaps(first, second) is expected
    assert overlaps(second, first) is expected


def test_shared_interval_is_the_intersection() -> None:
    shared = shared_interval(span((9, 0), (12, 0)), span((10, 0), (11, 0)))
    assert shared == span((10, 0), (11, 0))
    partial = shared_interval(span((9, 0), (11, 0)), span((10, 0), (12, 0)))
    assert partial == span((10, 0), (11, 0))


def test_touching_intervals_share_nothing() -> None:
    assert shared_interval(span((9, 0), (11, 0)), span((11, 0), (12, 0))) is None


# The plan's core cases (Implementation_Plans/01): the gap is end-to-start.
@pytest.mark.parametrize(
    ("second_start", "violated"),
    [
        ((13, 0), False),  # exactly 120 minutes passes
        ((13, 1), False),
        ((12, 59), True),  # 119 minutes fails
        ((11, 0), True),  # back to back
        ((12, 0), True),  # 60 minutes
    ],
)
def test_gap_of_exactly_120_minutes_passes_and_119_fails(
    second_start: tuple[int, int], violated: bool
) -> None:
    first = span((9, 0), (11, 0))
    second = Interval(at(*second_start), at(*second_start) + timedelta(hours=1))
    assert gap_violated(first, second, GAP) is violated
    assert gap_violated(second, first, GAP) is violated, "argument order must not matter"


def test_overlapping_intervals_always_violate_the_gap() -> None:
    assert gap_violated(span((9, 0), (12, 0)), span((10, 0), (11, 0)), GAP) is True


@pytest.mark.parametrize(
    ("required_minutes", "violated"),
    [(30, False), (60, False), (61, True), (90, True), (120, True)],
)
def test_the_gap_is_configurable(required_minutes: int, violated: bool) -> None:
    # The actual gap between 11:00 and 12:00 is 60 minutes: it meets a 60-minute rule exactly.
    first, second = span((9, 0), (11, 0)), span((12, 0), (13, 0))
    assert gap_violated(first, second, timedelta(minutes=required_minutes)) is violated


def test_buffer_window_follows_the_event_that_ends_first() -> None:
    earlier, later = span((9, 0), (11, 0)), span((12, 0), (13, 0))
    expected = span((11, 0), (13, 0))
    assert buffer_window(earlier, later, GAP) == expected
    assert buffer_window(later, earlier, GAP) == expected


def test_buffer_window_matches_the_contracts_md_example() -> None:
    # CONTRACTS.md: events under 120 minutes apart report a 09:00 to 11:00 window.
    first, second = span((7, 0), (9, 0)), span((10, 0), (11, 0))
    assert buffer_window(first, second, GAP) == span((9, 0), (11, 0))


def test_a_zero_or_negative_gap_is_rejected() -> None:
    first, second = span((9, 0), (11, 0)), span((12, 0), (13, 0))
    for bad in (timedelta(0), timedelta(minutes=-5)):
        with pytest.raises(ValueError, match="gap"):
            gap_violated(first, second, bad)
