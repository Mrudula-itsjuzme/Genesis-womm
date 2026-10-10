import json
from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

from hypothesis import given, settings
from hypothesis import strategies as st

from app.domain.enums import ConflictConstraint, ConflictType, EventStatus, OverrideScope, Severity
from app.domain.intervals import Interval
from app.domain.scheduling import Conflict
from app.services.codec import (
    conflict_from_json,
    conflict_to_json,
    event_from_json,
    event_snapshot,
    override_from_json,
    override_to_json,
    request_hash,
)
from app.services.ports import EventRecord, OverrideRecord

IST = timezone(timedelta(hours=5, minutes=30))
T0 = datetime(2026, 10, 20, 4, 30, tzinfo=UTC)


def an_event(**changes: object) -> EventRecord:
    base = EventRecord(
        id=UUID(int=1),
        club_id=UUID(int=2),
        title="Robotics Demo Day",
        description=None,
        start_at=T0,
        end_at=T0 + timedelta(hours=2),
        resource_id=UUID(int=3),
        expected_attendance=80,
        audience_tags=("all-years", "robotics"),
        status=EventStatus.CONFIRMED,
        revision=4,
        created_by=UUID(int=5),
        verified_by=UUID(int=6),
        verified_at=T0,
        evidence_id=UUID(int=7),
        is_synthetic=True,
        created_at=T0,
        updated_at=T0,
    )
    return base.but(**changes)


def a_conflict(**changes: object) -> Conflict:
    base = Conflict(
        type=ConflictType.VENUE_OVERLAP,
        severity=Severity.BLOCKING,
        constraint=ConflictConstraint.VENUE_OVERLAP,
        event_ids=(UUID(int=1), UUID(int=2)),
        window=Interval(T0, T0 + timedelta(hours=1)),
        message="Both events are confirmed for the same venue and their times overlap.",
        override_required=True,
    )
    return Conflict(**{**base.__dict__, **changes})


def test_an_event_snapshot_is_plain_json_and_round_trips() -> None:
    record = an_event()
    snapshot = event_snapshot(record)
    assert json.loads(json.dumps(snapshot)) == snapshot
    assert event_from_json(snapshot) == record


def test_an_event_with_nothing_optional_set_round_trips() -> None:
    record = an_event(
        description=None,
        resource_id=None,
        expected_attendance=None,
        audience_tags=(),
        status=EventStatus.DRAFT,
        verified_by=None,
        verified_at=None,
        evidence_id=None,
    )
    assert event_from_json(event_snapshot(record)) == record


def test_snapshot_values_are_strings_numbers_lists_and_nulls_only() -> None:
    snapshot = event_snapshot(an_event())
    assert snapshot["id"] == str(UUID(int=1))
    assert snapshot["status"] == "CONFIRMED"
    assert snapshot["audience_tags"] == ["all-years", "robotics"]
    assert snapshot["start_at"] == "2026-10-20T04:30:00+00:00"


def test_times_keep_the_same_instant_whatever_zone_they_arrive_in() -> None:
    local = datetime(2026, 10, 20, 10, 0, tzinfo=IST)
    record = an_event(start_at=local, end_at=local + timedelta(hours=1))
    restored = event_from_json(event_snapshot(record))
    assert restored.start_at == local
    assert restored.start_at.utcoffset() is not None


def test_a_conflict_round_trips() -> None:
    conflict = a_conflict()
    payload = conflict_to_json(conflict)
    assert json.loads(json.dumps(payload)) == payload
    assert conflict_from_json(payload) == conflict


def test_a_conflict_without_a_constraint_round_trips() -> None:
    conflict = a_conflict(
        type=ConflictType.UNKNOWN_AVAILABILITY,
        severity=Severity.INFO,
        constraint=None,
        event_ids=(UUID(int=1),),
        override_required=False,
    )
    assert conflict_from_json(conflict_to_json(conflict)) == conflict


def test_the_request_hash_ignores_key_order_and_is_stable() -> None:
    a = request_hash("CREATE_EVENT", {"title": "x", "club_id": UUID(int=1), "tags": ("a", "b")})
    b = request_hash("CREATE_EVENT", {"tags": ("a", "b"), "club_id": UUID(int=1), "title": "x"})
    assert a == b
    assert len(a) == 64
    assert a == request_hash(
        "CREATE_EVENT", {"title": "x", "club_id": UUID(int=1), "tags": ["a", "b"]}
    )


def test_the_request_hash_changes_with_the_action_or_any_value() -> None:
    base = request_hash("CREATE_EVENT", {"title": "x", "start_at": T0})
    assert base != request_hash("TRANSITION_EVENT", {"title": "x", "start_at": T0})
    assert base != request_hash("CREATE_EVENT", {"title": "y", "start_at": T0})
    assert base != request_hash(
        "CREATE_EVENT", {"title": "x", "start_at": T0 + timedelta(minutes=1)}
    )


def test_the_same_instant_in_two_zones_hashes_the_same() -> None:
    assert request_hash("A", {"at": datetime(2026, 10, 20, 10, 0, tzinfo=IST)}) == request_hash(
        "A", {"at": datetime(2026, 10, 20, 4, 30, tzinfo=UTC)}
    )


@settings(max_examples=200, deadline=None)
@given(
    st.text(min_size=1, max_size=40),
    st.integers(1, 10_000),
    st.lists(st.text(min_size=1, max_size=10), max_size=5),
    st.sampled_from(list(EventStatus)),
)
def test_events_always_survive_a_json_round_trip(
    title: str, revision: int, tags: list[str], status: EventStatus
) -> None:
    verified = status is EventStatus.CONFIRMED
    record = an_event(
        title=title,
        revision=revision,
        audience_tags=tuple(tags),
        status=status,
        verified_by=UUID(int=6) if verified else None,
        verified_at=T0 if verified else None,
        evidence_id=UUID(int=7) if verified else None,
    )
    assert event_from_json(json.loads(json.dumps(event_snapshot(record)))) == record


def test_an_override_round_trips_with_and_without_evidence() -> None:
    for evidence in (None, UUID(int=9)):
        record = OverrideRecord(
            id=UUID(int=1),
            scope=OverrideScope.CAMPUS_GAP,
            event_a_id=UUID(int=2),
            event_b_id=UUID(int=3),
            reason="Concurrent campus activities approved by the registrar",
            authorized_by=UUID(int=4),
            evidence_id=evidence,
            created_at=T0,
        )
        payload = override_to_json(record)
        assert json.loads(json.dumps(payload)) == payload
        assert override_from_json(payload) == record
