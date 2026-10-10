"""Properties of the conflict engine that must hold for every input (spine AD-5, AD-6)."""

from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.strategies import DrawFn

from app.domain.enums import (
    AvailabilityState,
    ConflictConstraint,
    ConflictType,
    EventStatus,
    OverrideScope,
    Severity,
)
from app.domain.intervals import gap_violated, overlaps
from app.domain.scheduling import Conflict, Override, Policy, ScheduledEvent, evaluate

GAP = timedelta(minutes=120)
POLICY = Policy(campus_gap=GAP)
BASE = datetime(2026, 10, 20, tzinfo=UTC)
CLUB_A, CLUB_B = UUID(int=1001), UUID(int=1002)
VENUES = [UUID(int=2001), UUID(int=2002), None]
ACTIVE = [
    EventStatus.DRAFT,
    EventStatus.PROPOSED,
    EventStatus.SUBMITTED,
    EventStatus.CONFIRMED,
]
INACTIVE = [EventStatus.REJECTED, EventStatus.CANCELLED, EventStatus.COMPLETED]

PROPERTY = settings(max_examples=300, deadline=None)


@st.composite
def event(
    draw: DrawFn,
    ident: int,
    *,
    statuses: list[EventStatus] = ACTIVE,
    club: UUID | None = None,
) -> ScheduledEvent:
    start = BASE + timedelta(minutes=draw(st.integers(0, 24 * 60)))
    duration = timedelta(minutes=draw(st.integers(15, 360)))
    return ScheduledEvent(
        id=UUID(int=ident),
        club_id=club or draw(st.sampled_from([CLUB_A, CLUB_B])),
        status=draw(st.sampled_from(statuses)),
        start_at=start,
        end_at=start + duration,
        resource_id=draw(st.sampled_from(VENUES)),
    )


@st.composite
def same_club_pair(draw: DrawFn) -> tuple[ScheduledEvent, ScheduledEvent]:
    """Two active events of one club: neither is hidden from the other by the draft rule."""
    club = draw(st.sampled_from([CLUB_A, CLUB_B]))
    return draw(event(1, club=club)), draw(event(2, club=club))


def check(
    candidate: ScheduledEvent,
    others: list[ScheduledEvent],
    overrides: list[Override] | None = None,
    availability: AvailabilityState = AvailabilityState.CONFIRMED,
) -> list[Conflict]:
    return evaluate(candidate, others, overrides or [], POLICY, availability)


def constraints(conflicts: list[Conflict]) -> set[ConflictConstraint]:
    return {c.constraint for c in conflicts if c.constraint is not None}


def signature(conflict: Conflict) -> tuple[object, ...]:
    return (
        conflict.type,
        conflict.severity,
        conflict.constraint,
        conflict.window,
        conflict.message,
    )


@PROPERTY
@given(same_club_pair())
def test_each_constraint_is_exactly_its_own_pure_rule(
    pair: tuple[ScheduledEvent, ScheduledEvent],
) -> None:
    candidate, other = pair
    reported = constraints(check(candidate, [other]))
    same_venue = candidate.resource_id is not None and candidate.resource_id == other.resource_id
    now_overlap = overlaps(candidate.interval, other.interval)
    assert (ConflictConstraint.VENUE_OVERLAP in reported) == (same_venue and now_overlap)
    assert (ConflictConstraint.CAMPUS_GAP in reported) == gap_violated(
        candidate.interval, other.interval, GAP
    )


@PROPERTY
@given(same_club_pair())
def test_a_venue_overlap_is_always_also_a_campus_gap_violation(
    pair: tuple[ScheduledEvent, ScheduledEvent],
) -> None:
    reported = constraints(check(pair[0], [pair[1]]))
    if ConflictConstraint.VENUE_OVERLAP in reported:
        assert ConflictConstraint.CAMPUS_GAP in reported


@PROPERTY
@given(same_club_pair())
def test_the_result_is_the_same_whichever_event_is_the_candidate(
    pair: tuple[ScheduledEvent, ScheduledEvent],
) -> None:
    a, b = pair
    forward = check(a, [b])
    backward = check(b, [a])
    assert sorted(map(repr, map(signature, forward))) == sorted(map(repr, map(signature, backward)))
    for conflict in forward:
        assert conflict.event_ids == (a.id, b.id)
    for conflict in backward:
        assert conflict.event_ids == (b.id, a.id)


@PROPERTY
@given(same_club_pair())
def test_severity_comes_only_from_the_stage_of_both_events(
    pair: tuple[ScheduledEvent, ScheduledEvent],
) -> None:
    candidate, other = pair
    both_confirmed = (
        candidate.status is EventStatus.CONFIRMED and other.status is EventStatus.CONFIRMED
    )
    for conflict in check(candidate, [other]):
        if both_confirmed:
            assert conflict.severity is Severity.BLOCKING
            assert conflict.type in {ConflictType.VENUE_OVERLAP, ConflictType.CAMPUS_GAP_VIOLATION}
            assert conflict.override_required is True
        else:
            assert conflict.severity is Severity.WARNING
            assert conflict.type is ConflictType.TENTATIVE_OVERLAP
            assert conflict.override_required is False


@PROPERTY
@given(same_club_pair())
def test_a_campus_gap_override_never_touches_a_venue_overlap(
    pair: tuple[ScheduledEvent, ScheduledEvent],
) -> None:
    candidate, other = pair
    waiver = Override(scope=OverrideScope.CAMPUS_GAP, event_ids=frozenset({candidate.id, other.id}))
    before = check(candidate, [other])
    after = check(candidate, [other], [waiver])
    venue = [c for c in before if c.constraint is ConflictConstraint.VENUE_OVERLAP]
    assert [c for c in after if c.constraint is ConflictConstraint.VENUE_OVERLAP] == venue
    assert ConflictConstraint.CAMPUS_GAP not in constraints(after)


@PROPERTY
@given(same_club_pair())
def test_a_venue_override_never_touches_the_campus_gap(
    pair: tuple[ScheduledEvent, ScheduledEvent],
) -> None:
    candidate, other = pair
    waiver = Override(
        scope=OverrideScope.VENUE_OVERLAP, event_ids=frozenset({candidate.id, other.id})
    )
    before = check(candidate, [other])
    after = check(candidate, [other], [waiver])
    gap = [c for c in before if c.constraint is ConflictConstraint.CAMPUS_GAP]
    assert [c for c in after if c.constraint is ConflictConstraint.CAMPUS_GAP] == gap
    assert ConflictConstraint.VENUE_OVERLAP not in constraints(after)


@PROPERTY
@given(same_club_pair(), st.sets(st.sampled_from(list(OverrideScope))))
def test_overrides_can_only_remove_conflicts(
    pair: tuple[ScheduledEvent, ScheduledEvent], scopes: set[OverrideScope]
) -> None:
    candidate, other = pair
    waivers = [Override(scope=s, event_ids=frozenset({candidate.id, other.id})) for s in scopes]
    before = check(candidate, [other])
    after = check(candidate, [other], waivers)
    assert all(conflict in before for conflict in after)


@PROPERTY
@given(
    st.integers(0, 22 * 60),
    st.integers(15, 240),
    st.integers(15, 240),
)
def test_exactly_the_gap_passes_and_one_minute_less_fails_at_any_time_of_day(
    other_start: int, other_length: int, candidate_length: int
) -> None:
    hall, lab = VENUES[0], VENUES[1]
    other_start_at = BASE + timedelta(minutes=other_start)
    other_end = other_start_at + timedelta(minutes=other_length)
    other = ScheduledEvent(
        UUID(int=1), CLUB_A, EventStatus.CONFIRMED, other_start_at, other_end, hall
    )

    def candidate_starting(after: timedelta) -> ScheduledEvent:
        start = other_end + after
        return ScheduledEvent(
            UUID(int=2),
            CLUB_A,
            EventStatus.CONFIRMED,
            start,
            start + timedelta(minutes=candidate_length),
            lab,
        )

    assert check(candidate_starting(GAP), [other]) == []
    failing = check(candidate_starting(GAP - timedelta(minutes=1)), [other])
    assert [c.type for c in failing] == [ConflictType.CAMPUS_GAP_VIOLATION]
    assert failing[0].window.end - failing[0].window.start == GAP


@PROPERTY
@given(
    same_club_pair(),
    st.integers(-12 * 60, 14 * 60),
    st.integers(-12 * 60, 14 * 60),
)
def test_the_zone_the_inputs_are_written_in_never_changes_the_result(
    pair: tuple[ScheduledEvent, ScheduledEvent], offset_a: int, offset_b: int
) -> None:
    candidate, other = pair

    def rewritten(e: ScheduledEvent, minutes: int) -> ScheduledEvent:
        zone = timezone(timedelta(minutes=minutes))
        return ScheduledEvent(
            e.id,
            e.club_id,
            e.status,
            e.start_at.astimezone(zone),
            e.end_at.astimezone(zone),
            e.resource_id,
        )

    expected = check(candidate, [other])
    assert check(rewritten(candidate, offset_a), [rewritten(other, offset_b)]) == expected


@PROPERTY
@given(
    st.lists(st.integers(1, 40), min_size=2, max_size=8, unique=True).flatmap(
        lambda idents: st.tuples(
            event(100, club=CLUB_A),
            st.tuples(*[event(i, club=CLUB_A) for i in idents]),
            st.permutations(idents),
        )
    )
)
def test_the_order_of_the_other_events_never_changes_the_result(
    data: tuple[ScheduledEvent, tuple[ScheduledEvent, ...], list[int]],
) -> None:
    candidate, others, order = data
    by_id = {int(e.id.int): e for e in others}
    assert check(candidate, list(others)) == check(candidate, [by_id[i] for i in order])


@PROPERTY
@given(event(1, club=CLUB_A), event(2, statuses=INACTIVE))
def test_inactive_events_never_matter(candidate: ScheduledEvent, inactive: ScheduledEvent) -> None:
    assert check(candidate, [inactive]) == check(candidate, [])


@PROPERTY
@given(event(1, club=CLUB_A), event(2, statuses=[EventStatus.DRAFT], club=CLUB_B))
def test_another_clubs_draft_never_matters(
    candidate: ScheduledEvent, foreign_draft: ScheduledEvent
) -> None:
    assert check(candidate, [foreign_draft]) == check(candidate, [])


@PROPERTY
@given(event(1, club=CLUB_A), event(1, club=CLUB_B))
def test_an_event_is_never_compared_with_its_stored_self(
    candidate: ScheduledEvent, stored_copy: ScheduledEvent
) -> None:
    assert check(candidate, [stored_copy]) == check(candidate, [])


@PROPERTY
@given(
    event(1, club=CLUB_A),
    st.lists(event(2, club=CLUB_A), max_size=4),
    st.sampled_from(list(AvailabilityState)),
)
def test_output_is_ordered_blocking_then_warning_then_info_with_availability_rules(
    candidate: ScheduledEvent, others: list[ScheduledEvent], state: AvailabilityState
) -> None:
    result = evaluate(candidate, others, [], POLICY, state)
    order = {Severity.BLOCKING: 0, Severity.WARNING: 1, Severity.INFO: 2}
    ranks = [order[c.severity] for c in result]
    assert ranks == sorted(ranks)
    unknown = [c for c in result if c.type is ConflictType.UNKNOWN_AVAILABILITY]
    wanted = candidate.resource_id is not None and state is not AvailabilityState.CONFIRMED
    assert len(unknown) == (1 if wanted else 0)


@PROPERTY
@given(event(1, club=CLUB_A), st.lists(event(2, club=CLUB_A), max_size=6))
def test_events_beyond_the_gap_never_change_the_result(
    candidate: ScheduledEvent, others: list[ScheduledEvent]
) -> None:
    # The write path only loads events whose time falls inside the candidate's interval widened
    # by the campus gap. That must be exact: it cannot drop anything the engine would report.
    near = [
        other
        for other in others
        if other.start_at < candidate.end_at + GAP and other.end_at > candidate.start_at - GAP
    ]
    everything = evaluate(candidate, others, [], POLICY, AvailabilityState.UNKNOWN)
    assert evaluate(candidate, near, [], POLICY, AvailabilityState.UNKNOWN) == everything
