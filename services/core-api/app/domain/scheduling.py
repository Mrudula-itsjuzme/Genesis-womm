"""The deterministic conflict engine (spine AD-5, AD-6).

``evaluate`` is a pure function: the same inputs always give the same ordered output, and it
does no I/O. The LLM never decides scheduling truth; this does.

Two constraints are checked independently for every pair, and never short-circuit each other:

* ``VENUE_OVERLAP``: the same chosen venue and overlapping half-open intervals.
* ``CAMPUS_GAP``: any venue; violated unless one event ends at least the campus gap before the
  other starts. The gap is a CampusCue planning rule, not verified university policy.

Severity depends on the stage of both events. Only two CONFIRMED events can block; anything
less is a warning, so drafts and proposals always save. A candidate's ``status`` is the state
being evaluated: to check a confirmation, pass the candidate with ``status=CONFIRMED``.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from app.domain.enums import (
    AvailabilityState,
    ConflictConstraint,
    ConflictType,
    EventStatus,
    OverrideScope,
    Severity,
)
from app.domain.intervals import Interval, buffer_window, gap_violated, overlaps, shared_interval

_INACTIVE = frozenset({EventStatus.REJECTED, EventStatus.CANCELLED, EventStatus.COMPLETED})
_SEVERITY_RANK = {Severity.BLOCKING: 0, Severity.WARNING: 1, Severity.INFO: 2}
_CONSTRAINT_RANK = {ConflictConstraint.VENUE_OVERLAP: 0, ConflictConstraint.CAMPUS_GAP: 1}
_CONSTRAINT_OF_SCOPE = {
    OverrideScope.CAMPUS_GAP: ConflictConstraint.CAMPUS_GAP,
    OverrideScope.VENUE_OVERLAP: ConflictConstraint.VENUE_OVERLAP,
}
_LAST = datetime.max.replace(tzinfo=UTC)


@dataclass(frozen=True)
class Policy:
    campus_gap: timedelta

    def __post_init__(self) -> None:
        if self.campus_gap <= timedelta(0):
            raise ValueError("campus_gap must be a positive duration")

    @property
    def minutes(self) -> int:
        return int(self.campus_gap.total_seconds() // 60)


@dataclass(frozen=True)
class ScheduledEvent:
    """What the engine needs to know about an event. Times are normalised to UTC."""

    id: UUID
    club_id: UUID
    status: EventStatus
    start_at: datetime
    end_at: datetime
    resource_id: UUID | None

    def __post_init__(self) -> None:
        interval = Interval(self.start_at, self.end_at)
        object.__setattr__(self, "start_at", interval.start)
        object.__setattr__(self, "end_at", interval.end)

    @property
    def interval(self) -> Interval:
        return Interval(self.start_at, self.end_at)


@dataclass(frozen=True)
class Override:
    """A scoped, pair-specific exception. It waives one constraint for exactly one pair."""

    scope: OverrideScope
    event_ids: frozenset[UUID]

    def __post_init__(self) -> None:
        if len(self.event_ids) != 2:
            raise ValueError("an override names exactly two events")


@dataclass(frozen=True)
class Conflict:
    type: ConflictType
    severity: Severity
    constraint: ConflictConstraint | None
    event_ids: tuple[UUID, ...]  # the candidate first, then the other event
    window: Interval
    message: str
    override_required: bool


def _comparable(candidate: ScheduledEvent, other: ScheduledEvent) -> bool:
    if other.id == candidate.id or other.status in _INACTIVE:
        return False
    # Another club's draft is private: never compared, never revealed.
    return not (other.status is EventStatus.DRAFT and other.club_id != candidate.club_id)


def _conflict_type(constraint: ConflictConstraint, both_confirmed: bool) -> ConflictType:
    if not both_confirmed:
        return ConflictType.TENTATIVE_OVERLAP
    if constraint is ConflictConstraint.VENUE_OVERLAP:
        return ConflictType.VENUE_OVERLAP
    return ConflictType.CAMPUS_GAP_VIOLATION


def _message(
    constraint: ConflictConstraint, both_confirmed: bool, overlapping: bool, minutes: int
) -> str:
    if constraint is ConflictConstraint.VENUE_OVERLAP:
        if both_confirmed:
            return "Both events are confirmed for the same venue and their times overlap."
        return (
            "Another event is proposed for the same venue at an overlapping time. "
            "At least one of the two is not confirmed."
        )
    rule = (
        f"{minutes}-minute campus gap is a CampusCue planning rule, not verified university policy"
    )
    if overlapping:
        lead = f"The events overlap in time, and CampusCue plans for at least {minutes} minutes"
        lead += f" between campus events (the {rule})."
    else:
        lead = f"The events are less than {minutes} minutes apart. The {rule}."
    if both_confirmed:
        return lead
    return f"{lead} At least one of the two is not confirmed."


def _unknown_availability(candidate: ScheduledEvent, state: AvailabilityState) -> Conflict | None:
    if candidate.resource_id is None or state is AvailabilityState.CONFIRMED:
        return None
    if state is AvailabilityState.REQUESTED:
        message = "Availability has been requested but is not confirmed for this venue."
    else:
        message = (
            "No authoritative source confirms this venue is available. "
            "An empty calendar does not mean it is available."
        )
    return Conflict(
        type=ConflictType.UNKNOWN_AVAILABILITY,
        severity=Severity.INFO,
        constraint=None,
        event_ids=(candidate.id,),
        window=candidate.interval,
        message=message,
        override_required=False,
    )


def evaluate(
    candidate: ScheduledEvent,
    others: Iterable[ScheduledEvent],
    overrides: Iterable[Override],
    policy: Policy,
    venue_availability: AvailabilityState = AvailabilityState.UNKNOWN,
) -> list[Conflict]:
    """Every conflict for ``candidate``, blocking first, in a deterministic order.

    ``venue_availability`` is the evidence-backed state of the candidate's venue and defaults to
    UNKNOWN, because an empty calendar never proves a venue is free.
    """
    if candidate.status in _INACTIVE:
        return []

    waived = {(o.event_ids, _CONSTRAINT_OF_SCOPE[o.scope]) for o in overrides}
    mine = candidate.interval
    ranked: list[tuple[tuple[int, datetime, str, int], Conflict]] = []

    for other in others:
        if not _comparable(candidate, other):
            continue
        theirs = other.interval
        pair = frozenset({candidate.id, other.id})
        overlapping = overlaps(mine, theirs)
        same_venue = (
            candidate.resource_id is not None and candidate.resource_id == other.resource_id
        )
        both_confirmed = (
            candidate.status is EventStatus.CONFIRMED and other.status is EventStatus.CONFIRMED
        )

        violated = {
            ConflictConstraint.VENUE_OVERLAP: same_venue and overlapping,
            ConflictConstraint.CAMPUS_GAP: gap_violated(mine, theirs, policy.campus_gap),
        }
        for constraint, is_violated in violated.items():
            if not is_violated or (pair, constraint) in waived:
                continue
            window = shared_interval(mine, theirs) or buffer_window(mine, theirs, policy.campus_gap)
            conflict = Conflict(
                type=_conflict_type(constraint, both_confirmed),
                severity=Severity.BLOCKING if both_confirmed else Severity.WARNING,
                constraint=constraint,
                event_ids=(candidate.id, other.id),
                window=window,
                message=_message(constraint, both_confirmed, overlapping, policy.minutes),
                override_required=both_confirmed,
            )
            key = (
                _SEVERITY_RANK[conflict.severity],
                other.start_at,
                str(other.id),
                _CONSTRAINT_RANK[constraint],
            )
            ranked.append((key, conflict))

    unknown = _unknown_availability(candidate, venue_availability)
    if unknown is not None:
        ranked.append(((_SEVERITY_RANK[Severity.INFO], _LAST, "", 0), unknown))

    ranked.sort(key=lambda item: item[0])
    return [conflict for _, conflict in ranked]
