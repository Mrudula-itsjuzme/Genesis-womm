from datetime import UTC, datetime, timedelta, timezone

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.domain.enums import (
    AgentActionStatus,
    AgentActionType,
    ConflictType,
    ErrorCode,
    EventStatus,
    OverrideScope,
    Severity,
)
from app.domain.time import (
    FixedClock,
    InvalidIntervalError,
    NaiveDatetimeError,
    ensure_aware,
    ensure_interval,
    to_utc,
)

IST = timezone(timedelta(hours=5, minutes=30))


def test_conflict_types_are_the_five_classes_from_agents_md() -> None:
    assert {c.value for c in ConflictType} == {
        "VENUE_OVERLAP",
        "CAMPUS_GAP_VIOLATION",
        "TENTATIVE_OVERLAP",
        "DEPENDENCY_CONFLICT",
        "UNKNOWN_AVAILABILITY",
    }


def test_severity_values_match_contracts_md_lowercase() -> None:
    assert [s.value for s in Severity] == ["blocking", "warning", "info"]


def test_override_scopes_are_exactly_the_two_independent_constraints() -> None:
    assert {s.value for s in OverrideScope} == {"CAMPUS_GAP", "VENUE_OVERLAP"}


def test_event_status_keeps_tentative_stages_separate_from_confirmed() -> None:
    assert {s.value for s in EventStatus} == {
        "DRAFT",
        "PROPOSED",
        "SUBMITTED",
        "CONFIRMED",
        "COMPLETED",
        "REJECTED",
        "CANCELLED",
    }


def test_agent_actions_cannot_express_confirmation_or_override() -> None:
    names = {t.value for t in AgentActionType}
    assert names == {
        "CREATE_EVENT_DRAFT",
        "REQUEST_EVENT_CHANGE",
        "RECORD_COMMITMENT",
        "CREATE_FOLLOWUP_DRAFT",
    }
    assert not any("CONFIRM_EVENT" in n or "OVERRIDE" in n or "BOOK" in n for n in names)
    assert "PROPOSED" in {s.value for s in AgentActionStatus}


def test_error_codes_are_screaming_snake() -> None:
    for code in ErrorCode:
        assert code.value == code.name
        assert code.value.isupper()


def test_fixed_clock_returns_the_same_aware_utc_instant() -> None:
    instant = datetime(2026, 10, 10, 9, 0, tzinfo=IST)
    clock = FixedClock(instant)
    assert clock.now() == instant
    assert clock.now().utcoffset() == timedelta(0)


def test_fixed_clock_rejects_naive_datetime() -> None:
    with pytest.raises(NaiveDatetimeError):
        FixedClock(datetime(2026, 10, 10, 9, 0))


def test_ensure_aware_rejects_naive() -> None:
    with pytest.raises(NaiveDatetimeError):
        ensure_aware(datetime(2026, 10, 10, 9, 0))


def test_to_utc_converts_campus_local_time() -> None:
    local = datetime(2026, 10, 20, 9, 0, tzinfo=IST)
    assert to_utc(local) == datetime(2026, 10, 20, 3, 30, tzinfo=UTC)


# The API accepts only ISO 8601 with an explicit offset, which parses to a fixed-offset zone.
# Named DST zones are excluded on purpose: a local time inside a DST gap does not exist, and
# Python (PEP 495) refuses to compare such a value equal to any other zone's datetime.
fixed_offsets = st.builds(
    lambda minutes: timezone(timedelta(minutes=minutes)),
    st.integers(min_value=-12 * 60, max_value=14 * 60),
)


@given(
    st.datetimes(
        min_value=datetime(2000, 1, 2),
        max_value=datetime(2100, 1, 1),
        timezones=fixed_offsets,
    )
)
def test_to_utc_preserves_the_instant(value: datetime) -> None:
    assert to_utc(value) == value
    assert to_utc(value).utcoffset() == timedelta(0)


def test_ensure_interval_normalises_to_utc() -> None:
    start = datetime(2026, 10, 20, 9, 0, tzinfo=IST)
    end = datetime(2026, 10, 20, 11, 0, tzinfo=IST)
    s, e = ensure_interval(start, end)
    assert (s, e) == (
        datetime(2026, 10, 20, 3, 30, tzinfo=UTC),
        datetime(2026, 10, 20, 5, 30, tzinfo=UTC),
    )


@pytest.mark.parametrize("delta_minutes", [0, -1])
def test_ensure_interval_requires_start_before_end(delta_minutes: int) -> None:
    start = datetime(2026, 10, 20, 9, 0, tzinfo=UTC)
    with pytest.raises(InvalidIntervalError):
        ensure_interval(start, start + timedelta(minutes=delta_minutes))
