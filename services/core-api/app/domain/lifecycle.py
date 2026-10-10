"""Event and commitment lifecycles as transition tables (spine AD-7).

Status changes happen only through ``transition_event`` and ``transition_commitment``. No
request schema has a writable status. Moving into CONFIRMED needs an authorized actor and an
evidence reference, and records who verified it and when from that actor; organizer-supplied
progress is recorded as reported, never as verified. ACKNOWLEDGED is never CONFIRMED.

Checks run in a fixed order: authorization, then the transition table, then evidence. An
unauthorized actor therefore learns nothing about the current state.

Two moves are made by the system, not requested by a user, and are deliberately absent from
the user-facing tables: demoting a CONFIRMED event when its time or venue changes, and sending
live commitments back for revalidation when their event changes.
"""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.authz import Action, Actor, Decision, Resource, authorize
from app.domain.enums import CommitmentStatus, EventStatus
from app.domain.time import ensure_aware

E = EventStatus
C = CommitmentStatus


class TransitionError(Exception):
    """Base class for a refused lifecycle change."""


class InvalidTransitionError(TransitionError):
    def __init__(self, current: object, target: object) -> None:
        super().__init__(f"cannot move from {current} to {target}")
        self.current = current
        self.target = target


class NotAuthorizedError(TransitionError):
    def __init__(self, decision: Decision) -> None:
        super().__init__(f"not authorized: {decision.reason}")
        self.decision = decision


class EvidenceRequiredError(TransitionError):
    def __init__(self) -> None:
        super().__init__("an evidence reference is required to confirm")


@dataclass(frozen=True)
class Evidence:
    id: UUID


@dataclass(frozen=True)
class Verification:
    verified_by: UUID
    verified_at: datetime
    evidence_id: UUID


@dataclass(frozen=True)
class EventTransition:
    status: EventStatus
    verification: Verification | None


@dataclass(frozen=True)
class CommitmentTransition:
    status: CommitmentStatus
    verification: Verification | None
    reported_by: UUID | None


# ---- the tables -----------------------------------------------------------------------

_EVENT_EDGES: dict[EventStatus, frozenset[EventStatus]] = {
    E.DRAFT: frozenset({E.PROPOSED, E.CANCELLED}),
    E.PROPOSED: frozenset({E.SUBMITTED, E.REJECTED, E.CANCELLED}),
    E.SUBMITTED: frozenset({E.CONFIRMED, E.REJECTED, E.CANCELLED}),
    E.CONFIRMED: frozenset({E.COMPLETED, E.CANCELLED}),
    E.COMPLETED: frozenset(),
    E.REJECTED: frozenset(),
    E.CANCELLED: frozenset(),
}
_EVENT_ACTION: dict[EventStatus, Action] = {
    E.PROPOSED: Action.PROPOSE_EVENT,
    E.SUBMITTED: Action.SUBMIT_EVENT,
    E.CONFIRMED: Action.CONFIRM_EVENT,
    E.REJECTED: Action.REJECT_EVENT,
    E.CANCELLED: Action.CANCEL_EVENT,
    E.COMPLETED: Action.COMPLETE_EVENT,
}

_COMMITMENT_EDGES: dict[CommitmentStatus, frozenset[CommitmentStatus]] = {
    C.DRAFT: frozenset({C.REQUESTED}),
    C.REQUESTED: frozenset({C.ACKNOWLEDGED}),
    C.ACKNOWLEDGED: frozenset({C.CONDITIONALLY_CONFIRMED, C.CONFIRMED}),
    C.CONDITIONALLY_CONFIRMED: frozenset({C.CONFIRMED}),
    C.CONFIRMED: frozenset({C.CLOSED}),
    C.NEEDS_REVALIDATION: frozenset({C.REQUESTED, C.CLOSED}),
    C.CLOSED: frozenset(),
}
_COMMITMENT_ACTION: dict[CommitmentStatus, Action] = {
    C.REQUESTED: Action.REPORT_COMMITMENT,
    C.ACKNOWLEDGED: Action.REPORT_COMMITMENT,
    C.CONDITIONALLY_CONFIRMED: Action.REPORT_COMMITMENT,
    C.CONFIRMED: Action.VERIFY_COMMITMENT,
    C.CLOSED: Action.CLOSE_COMMITMENT,
}

_VERIFYING = frozenset({Action.CONFIRM_EVENT, Action.VERIFY_COMMITMENT})
_REPORTING = frozenset({Action.REPORT_COMMITMENT})
_REVALIDATION_SOURCES = frozenset(
    {C.REQUESTED, C.ACKNOWLEDGED, C.CONDITIONALLY_CONFIRMED, C.CONFIRMED}
)


# ---- the one place a step is checked --------------------------------------------------


def _check_step[S](
    current: S,
    target: S,
    *,
    edges: dict[S, frozenset[S]],
    actions: dict[S, Action],
    actor: Actor,
    club_id: UUID,
    evidence: Evidence | None,
    now: datetime,
) -> tuple[Action, Verification | None]:
    action = actions.get(target)
    if action is None:  # nothing can be requested into DRAFT, or into a system-only state
        raise InvalidTransitionError(current, target)

    decision = authorize(actor, action, Resource(club_id=club_id))
    if not decision.allowed:
        raise NotAuthorizedError(decision)

    if target not in edges.get(current, frozenset()):
        raise InvalidTransitionError(current, target)

    if action in _VERIFYING:
        if evidence is None:
            raise EvidenceRequiredError
        return action, Verification(actor.user_id, ensure_aware(now), evidence.id)
    return action, None


def transition_event(
    current: EventStatus,
    target: EventStatus,
    *,
    actor: Actor,
    club_id: UUID,
    evidence: Evidence | None,
    now: datetime,
) -> EventTransition:
    _, verification = _check_step(
        current,
        target,
        edges=_EVENT_EDGES,
        actions=_EVENT_ACTION,
        actor=actor,
        club_id=club_id,
        evidence=evidence,
        now=now,
    )
    return EventTransition(status=target, verification=verification)


def transition_commitment(
    current: CommitmentStatus,
    target: CommitmentStatus,
    *,
    actor: Actor,
    club_id: UUID,
    evidence: Evidence | None,
    now: datetime,
) -> CommitmentTransition:
    action, verification = _check_step(
        current,
        target,
        edges=_COMMITMENT_EDGES,
        actions=_COMMITMENT_ACTION,
        actor=actor,
        club_id=club_id,
        evidence=evidence,
        now=now,
    )
    return CommitmentTransition(
        status=target,
        verification=verification,
        reported_by=actor.user_id if action in _REPORTING else None,
    )


def event_action_for(target: EventStatus) -> Action | None:
    """The action an actor needs to move an event into ``target``, or None if no user can."""
    return _EVENT_ACTION.get(target)


# ---- system moves ---------------------------------------------------------------------


def demote_on_schedule_change(status: EventStatus) -> EventStatus:
    """A CONFIRMED event whose time or venue changes is no longer confirmed for the new slot."""
    return E.SUBMITTED if status is E.CONFIRMED else status


def mark_needs_revalidation(status: CommitmentStatus) -> CommitmentStatus:
    """Live commitments must be re-checked when their event changes; none carry forward."""
    return C.NEEDS_REVALIDATION if status in _REVALIDATION_SOURCES else status
