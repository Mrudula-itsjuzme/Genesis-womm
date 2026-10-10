"""The conflict engine (spine AD-5, AD-6) against the cases in Implementation_Plans/01."""

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

import pytest

from app.domain.enums import (
    AvailabilityState,
    ConflictConstraint,
    ConflictType,
    EventStatus,
    OverrideScope,
    Severity,
)
from app.domain.intervals import Interval
from app.domain.scheduling import Conflict, Override, Policy, ScheduledEvent, evaluate

POLICY = Policy(campus_gap=timedelta(minutes=120))
DAY = datetime(2026, 10, 20, tzinfo=UTC)
CLUB_A, CLUB_B = UUID(int=1001), UUID(int=1002)
HALL, LAB = UUID(int=2001), UUID(int=2002)
CONFIRMED, PROPOSED, DRAFT = EventStatus.CONFIRMED, EventStatus.PROPOSED, EventStatus.DRAFT

_next_id = iter(range(1, 10_000))


def at(hour: int, minute: int = 0) -> datetime:
    return DAY.replace(hour=hour, minute=minute)


def ev(
    start: tuple[int, int],
    end: tuple[int, int],
    *,
    status: EventStatus = CONFIRMED,
    venue: UUID | None = HALL,
    club: UUID = CLUB_A,
    ident: int | None = None,
) -> ScheduledEvent:
    return ScheduledEvent(
        id=UUID(int=ident if ident is not None else next(_next_id)),
        club_id=club,
        status=status,
        start_at=at(*start),
        end_at=at(*end),
        resource_id=venue,
    )


def kinds(conflicts: list[Conflict]) -> list[tuple[ConflictType, Severity]]:
    return [(c.type, c.severity) for c in conflicts]


def without_availability(conflicts: list[Conflict]) -> list[Conflict]:
    return [c for c in conflicts if c.type is not ConflictType.UNKNOWN_AVAILABILITY]


def run(
    candidate: ScheduledEvent,
    others: list[ScheduledEvent],
    overrides: list[Override] | None = None,
    availability: AvailabilityState = AvailabilityState.CONFIRMED,
) -> list[Conflict]:
    """CONFIRMED availability keeps UNKNOWN_AVAILABILITY out of the way unless a test wants it."""
    return evaluate(candidate, others, overrides or [], POLICY, availability)


def override(scope: OverrideScope, a: ScheduledEvent, b: ScheduledEvent) -> Override:
    return Override(scope=scope, event_ids=frozenset({a.id, b.id}))


# ---- the plan's core interval cases ---------------------------------------------------


def test_gap_passes_at_exactly_120_minutes() -> None:
    candidate = ev((13, 0), (14, 0), venue=LAB)
    assert run(candidate, [ev((9, 0), (11, 0))]) == []


def test_gap_fails_at_119_minutes() -> None:
    candidate = ev((12, 59), (14, 0), venue=LAB)
    result = run(candidate, [ev((9, 0), (11, 0))])
    assert kinds(result) == [(ConflictType.CAMPUS_GAP_VIOLATION, Severity.BLOCKING)]


def test_same_venue_overlap_violates_both_constraints_independently() -> None:
    candidate, other = ev((10, 0), (11, 0)), ev((9, 0), (12, 0))
    result = run(candidate, [other])
    assert sorted(c.constraint for c in result if c.constraint) == sorted(
        [ConflictConstraint.VENUE_OVERLAP, ConflictConstraint.CAMPUS_GAP]
    )
    assert {c.type for c in result} == {
        ConflictType.VENUE_OVERLAP,
        ConflictType.CAMPUS_GAP_VIOLATION,
    }
    assert all(c.severity is Severity.BLOCKING and c.override_required for c in result)


def test_different_venues_30_minutes_apart_violate_only_the_campus_gap() -> None:
    candidate = ev((11, 30), (12, 30), venue=LAB)
    result = run(candidate, [ev((9, 0), (11, 0), venue=HALL)])
    assert [c.constraint for c in result] == [ConflictConstraint.CAMPUS_GAP]


def test_back_to_back_at_one_venue_passes_the_venue_check_but_fails_the_gap() -> None:
    candidate = ev((11, 0), (12, 0))
    result = run(candidate, [ev((9, 0), (11, 0))])
    assert [c.constraint for c in result] == [ConflictConstraint.CAMPUS_GAP]
    assert result[0].type is ConflictType.CAMPUS_GAP_VIOLATION


def test_touching_intervals_at_one_venue_do_not_overlap() -> None:
    result = run(ev((11, 0), (12, 0)), [ev((9, 0), (11, 0))])
    assert ConflictType.VENUE_OVERLAP not in {c.type for c in result}


def test_a_candidate_is_never_compared_with_itself() -> None:
    candidate = ev((9, 0), (11, 0), ident=77)
    assert run(candidate, [candidate]) == []
    moved = ev((9, 30), (11, 30), ident=77)  # the stored copy of the same event
    assert run(moved, [candidate]) == []


# ---- which events count ---------------------------------------------------------------


@pytest.mark.parametrize(
    "status", [EventStatus.CANCELLED, EventStatus.REJECTED, EventStatus.COMPLETED]
)
def test_inactive_events_impose_no_constraint(status: EventStatus) -> None:
    assert run(ev((9, 0), (11, 0)), [ev((10, 0), (12, 0), status=status)]) == []


@pytest.mark.parametrize(
    "status", [EventStatus.CANCELLED, EventStatus.REJECTED, EventStatus.COMPLETED]
)
def test_an_inactive_candidate_has_nothing_to_check(status: EventStatus) -> None:
    candidate = ev((9, 0), (11, 0), status=status)
    assert run(candidate, [ev((10, 0), (12, 0))], availability=AvailabilityState.UNKNOWN) == []


def test_another_clubs_draft_is_private_and_never_compared() -> None:
    candidate = ev((9, 0), (11, 0), club=CLUB_A)
    assert run(candidate, [ev((10, 0), (12, 0), status=DRAFT, club=CLUB_B)]) == []


def test_the_owning_clubs_own_draft_is_compared_as_a_warning() -> None:
    candidate = ev((9, 0), (11, 0), status=PROPOSED, club=CLUB_A)
    result = run(candidate, [ev((10, 0), (12, 0), status=DRAFT, club=CLUB_A)])
    assert kinds(result) == [
        (ConflictType.TENTATIVE_OVERLAP, Severity.WARNING),
        (ConflictType.TENTATIVE_OVERLAP, Severity.WARNING),
    ]


def test_a_draft_candidate_still_sees_other_clubs_real_events() -> None:
    candidate = ev((9, 0), (11, 0), status=DRAFT, club=CLUB_A)
    result = run(candidate, [ev((10, 0), (12, 0), status=CONFIRMED, club=CLUB_B)])
    assert {c.type for c in result} == {ConflictType.TENTATIVE_OVERLAP}


# ---- severity by stage ----------------------------------------------------------------


@pytest.mark.parametrize(
    ("candidate_status", "other_status"),
    [
        (PROPOSED, CONFIRMED),
        (CONFIRMED, EventStatus.SUBMITTED),
        (PROPOSED, PROPOSED),
        (DRAFT, EventStatus.SUBMITTED),
    ],
)
def test_unless_both_are_confirmed_a_conflict_is_a_warning_that_needs_no_override(
    candidate_status: EventStatus, other_status: EventStatus
) -> None:
    result = run(
        ev((10, 0), (11, 0), status=candidate_status, club=CLUB_A),
        [ev((9, 0), (12, 0), status=other_status, club=CLUB_A)],
    )
    assert result, "an overlap must be reported"
    for conflict in result:
        assert conflict.type is ConflictType.TENTATIVE_OVERLAP
        assert conflict.severity is Severity.WARNING
        assert conflict.override_required is False
        assert conflict.constraint in set(ConflictConstraint)


def test_tentative_overlap_names_which_constraint_was_violated() -> None:
    candidate = ev((10, 0), (11, 0), status=PROPOSED)
    result = run(candidate, [ev((9, 0), (12, 0))])
    assert {c.constraint for c in result} == {
        ConflictConstraint.VENUE_OVERLAP,
        ConflictConstraint.CAMPUS_GAP,
    }


def test_only_two_confirmed_events_can_block() -> None:
    result = run(ev((10, 0), (11, 0)), [ev((9, 0), (12, 0))])
    assert all(c.severity is Severity.BLOCKING for c in result)
    assert all(c.override_required for c in result)


# ---- overrides ------------------------------------------------------------------------


def test_a_campus_gap_override_never_removes_a_venue_overlap() -> None:
    candidate, other = ev((10, 0), (11, 0)), ev((9, 0), (12, 0))
    result = run(candidate, [other], [override(OverrideScope.CAMPUS_GAP, candidate, other)])
    assert kinds(result) == [(ConflictType.VENUE_OVERLAP, Severity.BLOCKING)]


def test_a_venue_overlap_override_leaves_the_campus_gap() -> None:
    candidate, other = ev((10, 0), (11, 0)), ev((9, 0), (12, 0))
    result = run(candidate, [other], [override(OverrideScope.VENUE_OVERLAP, candidate, other)])
    assert kinds(result) == [(ConflictType.CAMPUS_GAP_VIOLATION, Severity.BLOCKING)]


def test_both_overrides_together_clear_the_pair() -> None:
    candidate, other = ev((10, 0), (11, 0)), ev((9, 0), (12, 0))
    overrides = [
        override(OverrideScope.CAMPUS_GAP, candidate, other),
        override(OverrideScope.VENUE_OVERLAP, candidate, other),
    ]
    assert run(candidate, [other], overrides) == []


def test_an_override_covers_exactly_its_pair() -> None:
    candidate, waived, unwaived = ev((10, 0), (11, 0)), ev((9, 0), (12, 0)), ev((9, 30), (10, 30))
    overrides = [
        override(OverrideScope.CAMPUS_GAP, candidate, waived),
        override(OverrideScope.VENUE_OVERLAP, candidate, waived),
    ]
    result = run(candidate, [waived, unwaived], overrides)
    assert {c.event_ids[1] for c in result} == {unwaived.id}


def test_an_override_for_other_events_does_not_apply() -> None:
    candidate, other, stranger = ev((10, 0), (11, 0)), ev((9, 0), (12, 0)), ev((15, 0), (16, 0))
    result = run(candidate, [other], [override(OverrideScope.CAMPUS_GAP, candidate, stranger)])
    assert len(result) == 2


def test_the_pair_in_an_override_is_unordered() -> None:
    candidate, other = ev((10, 0), (11, 0)), ev((9, 0), (12, 0))
    flipped = Override(
        scope=OverrideScope.CAMPUS_GAP, event_ids=frozenset({other.id, candidate.id})
    )
    assert len(run(candidate, [other], [flipped])) == 1


def test_an_override_also_waives_the_warning_form_of_its_constraint() -> None:
    candidate = ev((10, 0), (11, 0), status=PROPOSED)
    other = ev((9, 0), (12, 0))
    result = run(candidate, [other], [override(OverrideScope.CAMPUS_GAP, candidate, other)])
    assert [c.constraint for c in result] == [ConflictConstraint.VENUE_OVERLAP]


# ---- venues and availability ----------------------------------------------------------


def test_two_events_with_no_venue_chosen_never_conflict_on_venue() -> None:
    result = run(ev((10, 0), (11, 0), venue=None), [ev((9, 0), (12, 0), venue=None)])
    assert [c.constraint for c in result] == [ConflictConstraint.CAMPUS_GAP]


def test_a_venue_against_no_venue_is_not_a_venue_overlap() -> None:
    result = run(ev((10, 0), (11, 0), venue=HALL), [ev((9, 0), (12, 0), venue=None)])
    assert [c.constraint for c in result] == [ConflictConstraint.CAMPUS_GAP]


def test_a_venue_without_evidence_is_reported_as_unknown_never_as_free() -> None:
    result = evaluate(ev((10, 0), (11, 0)), [], [], POLICY, AvailabilityState.UNKNOWN)
    (conflict,) = result
    assert (conflict.type, conflict.severity) == (ConflictType.UNKNOWN_AVAILABILITY, Severity.INFO)
    assert conflict.override_required is False
    assert conflict.constraint is None
    assert "free" not in conflict.message.lower()
    assert "empty calendar" in conflict.message.lower()


def test_availability_defaults_to_unknown() -> None:
    (conflict,) = evaluate(ev((10, 0), (11, 0)), [], [], POLICY)
    assert conflict.type is ConflictType.UNKNOWN_AVAILABILITY


def test_requested_is_still_not_confirmed() -> None:
    result = evaluate(ev((10, 0), (11, 0)), [], [], POLICY, AvailabilityState.REQUESTED)
    assert [c.type for c in result] == [ConflictType.UNKNOWN_AVAILABILITY]
    assert "requested" in result[0].message.lower()


def test_confirmed_availability_removes_the_unknown_notice() -> None:
    assert evaluate(ev((10, 0), (11, 0)), [], [], POLICY, AvailabilityState.CONFIRMED) == []


def test_no_venue_means_nothing_to_report_about_availability() -> None:
    assert evaluate(ev((10, 0), (11, 0), venue=None), [], [], POLICY) == []


def test_an_empty_calendar_does_not_prove_availability() -> None:
    result = evaluate(ev((10, 0), (11, 0)), [], [], POLICY, AvailabilityState.UNKNOWN)
    assert result
    assert result[0].type is ConflictType.UNKNOWN_AVAILABILITY


# ---- shape of the result --------------------------------------------------------------


def test_event_ids_are_the_candidate_then_the_other() -> None:
    candidate, other = ev((10, 0), (11, 0)), ev((9, 0), (12, 0))
    for conflict in run(candidate, [other]):
        assert conflict.event_ids == (candidate.id, other.id)


def test_unknown_availability_names_only_the_candidate() -> None:
    candidate = ev((10, 0), (11, 0))
    (conflict,) = evaluate(candidate, [], [], POLICY)
    assert conflict.event_ids == (candidate.id,)
    assert conflict.window == Interval(at(10), at(11))


def test_an_overlap_window_is_the_shared_interval() -> None:
    result = run(ev((10, 0), (11, 0)), [ev((9, 0), (10, 30))])
    for conflict in result:
        assert conflict.window == Interval(at(10), at(10, 30))


def test_nested_events_at_different_venues_report_the_overlap_not_a_distant_buffer() -> None:
    result = run(ev((10, 0), (11, 0), venue=LAB), [ev((9, 0), (13, 0), venue=HALL)])
    (conflict,) = result
    assert conflict.window == Interval(at(10), at(11))


def test_a_gap_violation_without_overlap_reports_the_protected_buffer() -> None:
    result = run(ev((12, 0), (13, 0), venue=LAB), [ev((9, 0), (11, 0), venue=HALL)])
    (conflict,) = result
    assert conflict.window == Interval(at(11), at(13))
    assert conflict.window.end - conflict.window.start == timedelta(minutes=120)


def test_the_buffer_follows_the_event_that_ends_first_whichever_is_the_candidate() -> None:
    earlier, later = ev((9, 0), (11, 0), venue=HALL), ev((12, 0), (13, 0), venue=LAB)
    assert run(later, [earlier])[0].window == run(earlier, [later])[0].window


def test_messages_call_the_gap_a_planning_rule() -> None:
    (conflict,) = run(ev((12, 0), (13, 0), venue=LAB), [ev((9, 0), (11, 0), venue=HALL)])
    assert "120" in conflict.message
    assert "planning rule" in conflict.message
    assert "policy" in conflict.message


def test_blocking_conflicts_come_first_then_warnings_then_info() -> None:
    candidate = ev((10, 0), (11, 0), status=CONFIRMED)
    others = [
        ev((9, 0), (12, 0), status=PROPOSED),
        ev((9, 30), (10, 30), status=CONFIRMED, venue=LAB),
    ]
    result = evaluate(candidate, others, [], POLICY, AvailabilityState.UNKNOWN)
    ranks = [
        {Severity.BLOCKING: 0, Severity.WARNING: 1, Severity.INFO: 2}[c.severity] for c in result
    ]
    assert ranks == sorted(ranks)
    assert result[-1].type is ConflictType.UNKNOWN_AVAILABILITY


def test_output_does_not_depend_on_the_order_of_the_other_events() -> None:
    candidate = ev((12, 0), (13, 0), venue=LAB)
    others = [ev((8 + i, 0), (9 + i, 0), venue=HALL if i % 2 else LAB) for i in range(6)]
    expected = run(candidate, others)
    reordered = [others[::-1], *(others[i:] + others[:i] for i in range(1, len(others)))]
    for variant in reordered:
        assert run(candidate, variant) == expected


def test_each_other_event_is_reported_separately() -> None:
    candidate = ev((10, 0), (11, 0))
    first, second = ev((9, 0), (10, 30)), ev((10, 30), (12, 0))
    result = run(candidate, [first, second])
    assert {c.event_ids[1] for c in result} == {first.id, second.id}


# ---- policy and time zones ------------------------------------------------------------


def test_the_gap_comes_from_policy_not_a_constant() -> None:
    candidate, other = ev((12, 0), (13, 0), venue=LAB), ev((9, 0), (11, 0), venue=HALL)
    assert run(candidate, [other])  # 60 minutes apart violates a 120-minute rule
    relaxed = Policy(campus_gap=timedelta(minutes=60))
    assert evaluate(candidate, [other], [], relaxed, AvailabilityState.CONFIRMED) == []


def test_a_policy_gap_must_be_positive() -> None:
    for bad in (timedelta(0), timedelta(minutes=-1)):
        with pytest.raises(ValueError, match="gap"):
            Policy(campus_gap=bad)


def test_results_do_not_depend_on_the_zone_the_inputs_are_written_in() -> None:
    ist = timezone(timedelta(hours=5, minutes=30))
    pacific = timezone(timedelta(hours=-8))

    def in_zone(event: ScheduledEvent, zone: timezone) -> ScheduledEvent:
        return ScheduledEvent(
            id=event.id,
            club_id=event.club_id,
            status=event.status,
            start_at=event.start_at.astimezone(zone),
            end_at=event.end_at.astimezone(zone),
            resource_id=event.resource_id,
        )

    candidate, other = ev((12, 59), (14, 0), venue=LAB), ev((9, 0), (11, 0), venue=HALL)
    baseline = run(candidate, [other])
    assert run(in_zone(candidate, ist), [in_zone(other, pacific)]) == baseline


def test_an_event_needs_aware_times_and_a_real_interval() -> None:
    with pytest.raises(ValueError, match="offset"):
        ScheduledEvent(
            id=UUID(int=1),
            club_id=CLUB_A,
            status=CONFIRMED,
            start_at=datetime(2026, 10, 20, 9),
            end_at=at(10),
            resource_id=None,
        )
    with pytest.raises(ValueError, match="strictly before"):
        ScheduledEvent(
            id=UUID(int=1),
            club_id=CLUB_A,
            status=CONFIRMED,
            start_at=at(10),
            end_at=at(10),
            resource_id=None,
        )


def test_gap_arithmetic_uses_instants_so_a_dst_change_cannot_hide_a_violation() -> None:
    # The campus (IST) has no DST, but the engine must not depend on that. New York springs
    # forward at 02:00 on 2026-03-08. Event A ends 00:30 EST; event B starts 03:00 EDT, which is
    # only 90 real minutes later. Wall-clock arithmetic (00:30 + 120 min = 02:30 <= 03:00)
    # would wrongly accept it.
    new_york = ZoneInfo("America/New_York")
    first = ScheduledEvent(
        id=UUID(int=1),
        club_id=CLUB_A,
        status=CONFIRMED,
        start_at=datetime(2026, 3, 7, 22, 0, tzinfo=new_york),
        end_at=datetime(2026, 3, 8, 0, 30, tzinfo=new_york),
        resource_id=HALL,
    )
    second = ScheduledEvent(
        id=UUID(int=2),
        club_id=CLUB_A,
        status=CONFIRMED,
        start_at=datetime(2026, 3, 8, 3, 0, tzinfo=new_york),
        end_at=datetime(2026, 3, 8, 4, 0, tzinfo=new_york),
        resource_id=LAB,
    )
    assert second.start_at - first.end_at == timedelta(minutes=90)
    result = run(second, [first])
    assert [c.type for c in result] == [ConflictType.CAMPUS_GAP_VIOLATION]
