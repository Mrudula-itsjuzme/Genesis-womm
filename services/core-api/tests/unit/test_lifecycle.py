"""Event and commitment lifecycles are transition tables (spine AD-7)."""

from dataclasses import replace
from datetime import UTC, datetime
from itertools import product
from uuid import UUID

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.domain.authz import Action, Actor, Reason
from app.domain.enums import CommitmentStatus, EventStatus, Role
from app.domain.lifecycle import (
    CommitmentTransition,
    EventTransition,
    Evidence,
    EvidenceRequiredError,
    InvalidTransitionError,
    NotAuthorizedError,
    demote_on_schedule_change,
    event_action_for,
    mark_needs_revalidation,
    transition_commitment,
    transition_event,
)

CLUB = UUID(int=1001)
USER = UUID(int=1)
EVIDENCE = Evidence(id=UUID(int=9001))
NOW = datetime(2026, 10, 20, 4, 0, tzinfo=UTC)

ADMIN = Actor(user_id=USER, campus_admin=True)
CLUB_ADMIN = Actor(user_id=USER, memberships={CLUB: Role.CLUB_ADMIN})
ORGANIZER = Actor(user_id=USER, memberships={CLUB: Role.ORGANIZER})
STRANGER = Actor(user_id=USER)

E = EventStatus
C = CommitmentStatus

# The spine's event diagram, minus CONFIRMED -> SUBMITTED, which the system does on a change.
EVENT_EDGES = {
    (E.DRAFT, E.PROPOSED),
    (E.PROPOSED, E.SUBMITTED),
    (E.SUBMITTED, E.CONFIRMED),
    (E.CONFIRMED, E.COMPLETED),
    (E.PROPOSED, E.REJECTED),
    (E.SUBMITTED, E.REJECTED),
    (E.DRAFT, E.CANCELLED),
    (E.PROPOSED, E.CANCELLED),
    (E.SUBMITTED, E.CANCELLED),
    (E.CONFIRMED, E.CANCELLED),
}
# The spine's commitment diagram, minus the "event change" edges, which the system does.
COMMITMENT_EDGES = {
    (C.DRAFT, C.REQUESTED),
    (C.REQUESTED, C.ACKNOWLEDGED),
    (C.ACKNOWLEDGED, C.CONDITIONALLY_CONFIRMED),
    (C.ACKNOWLEDGED, C.CONFIRMED),
    (C.CONDITIONALLY_CONFIRMED, C.CONFIRMED),
    (C.NEEDS_REVALIDATION, C.REQUESTED),
    (C.CONFIRMED, C.CLOSED),
    (C.NEEDS_REVALIDATION, C.CLOSED),
}
REVALIDATION_SOURCES = {C.REQUESTED, C.ACKNOWLEDGED, C.CONDITIONALLY_CONFIRMED, C.CONFIRMED}


def event_step(
    current: EventStatus,
    target: EventStatus,
    actor: Actor = ADMIN,
    evidence: Evidence | None = EVIDENCE,
) -> EventTransition:
    return transition_event(current, target, actor=actor, club_id=CLUB, evidence=evidence, now=NOW)


def commitment_step(
    current: CommitmentStatus,
    target: CommitmentStatus,
    actor: Actor = ADMIN,
    evidence: Evidence | None = EVIDENCE,
) -> CommitmentTransition:
    return transition_commitment(
        current, target, actor=actor, club_id=CLUB, evidence=evidence, now=NOW
    )


# ---- the tables equal the spine's diagrams --------------------------------------------


def test_event_edges_are_exactly_the_spines_diagram() -> None:
    allowed = set()
    for current, target in product(EventStatus, EventStatus):
        try:
            event_step(current, target)
        except InvalidTransitionError:
            continue
        allowed.add((current, target))
    assert allowed == EVENT_EDGES


def test_commitment_edges_are_exactly_the_spines_diagram() -> None:
    allowed = set()
    for current, target in product(CommitmentStatus, CommitmentStatus):
        try:
            commitment_step(current, target)
        except InvalidTransitionError:
            continue
        allowed.add((current, target))
    assert allowed == COMMITMENT_EDGES


@pytest.mark.parametrize("terminal", [E.COMPLETED, E.REJECTED, E.CANCELLED])
def test_terminal_event_states_have_no_exit(terminal: EventStatus) -> None:
    for target in EventStatus:
        with pytest.raises(InvalidTransitionError):
            event_step(terminal, target)


def test_an_event_cannot_skip_submission_on_the_way_to_confirmed() -> None:
    for start in (E.DRAFT, E.PROPOSED):
        with pytest.raises(InvalidTransitionError):
            event_step(start, E.CONFIRMED)


def test_a_status_cannot_transition_to_itself() -> None:
    for status in EventStatus:
        with pytest.raises(InvalidTransitionError):
            event_step(status, status)
    for commitment in CommitmentStatus:
        with pytest.raises(InvalidTransitionError):
            commitment_step(commitment, commitment)


def test_nothing_transitions_back_to_draft() -> None:
    for status in EventStatus:
        with pytest.raises(InvalidTransitionError):
            event_step(status, E.DRAFT)


# ---- confirmation needs authority and evidence ----------------------------------------


def test_confirming_an_event_records_who_verified_it_from_the_actor_and_when() -> None:
    result = event_step(E.SUBMITTED, E.CONFIRMED, ADMIN, EVIDENCE)
    assert result.status is E.CONFIRMED
    assert result.verification is not None
    assert result.verification.verified_by == ADMIN.user_id
    assert result.verification.verified_at == NOW
    assert result.verification.evidence_id == EVIDENCE.id


def test_confirming_without_evidence_is_refused() -> None:
    with pytest.raises(EvidenceRequiredError):
        event_step(E.SUBMITTED, E.CONFIRMED, ADMIN, evidence=None)


@pytest.mark.parametrize("actor", [CLUB_ADMIN, ORGANIZER, STRANGER])
def test_only_a_campus_admin_confirms_an_event(actor: Actor) -> None:
    with pytest.raises(NotAuthorizedError) as refused:
        event_step(E.SUBMITTED, E.CONFIRMED, actor, EVIDENCE)
    assert refused.value.decision.reason is Reason.NOT_CAMPUS_ADMIN


def test_an_agent_acting_for_an_admin_cannot_confirm() -> None:
    agent = replace(ADMIN, via_agent=True)
    with pytest.raises(NotAuthorizedError) as refused:
        event_step(E.SUBMITTED, E.CONFIRMED, agent, EVIDENCE)
    assert refused.value.decision.reason is Reason.AGENT_NOT_ALLOWED


def test_transitions_other_than_confirmation_carry_no_verification() -> None:
    assert event_step(E.DRAFT, E.PROPOSED, ORGANIZER, evidence=None).verification is None
    assert event_step(E.SUBMITTED, E.REJECTED, ADMIN, evidence=None).verification is None


def test_each_event_step_asks_the_right_role() -> None:
    assert event_step(E.DRAFT, E.PROPOSED, ORGANIZER, None).status is E.PROPOSED
    assert event_step(E.PROPOSED, E.SUBMITTED, ORGANIZER, None).status is E.SUBMITTED
    assert event_step(E.DRAFT, E.CANCELLED, CLUB_ADMIN, None).status is E.CANCELLED
    assert event_step(E.CONFIRMED, E.COMPLETED, CLUB_ADMIN, None).status is E.COMPLETED
    with pytest.raises(NotAuthorizedError):
        event_step(E.DRAFT, E.CANCELLED, ORGANIZER, None)
    with pytest.raises(NotAuthorizedError):
        event_step(E.PROPOSED, E.REJECTED, CLUB_ADMIN, None)


def test_an_organizer_of_another_club_cannot_move_this_clubs_event() -> None:
    other = Actor(user_id=USER, memberships={UUID(int=2002): Role.CLUB_ADMIN})
    with pytest.raises(NotAuthorizedError) as refused:
        event_step(E.DRAFT, E.PROPOSED, other, None)
    assert refused.value.decision.reason is Reason.NOT_IN_CLUB


# ---- the order of the checks ----------------------------------------------------------


def test_authorization_is_checked_before_the_table_so_nothing_leaks_about_state() -> None:
    # A stranger asking for a nonsense transition is told "not allowed", not "invalid".
    with pytest.raises(NotAuthorizedError):
        event_step(E.COMPLETED, E.PROPOSED, STRANGER, EVIDENCE)


def test_the_table_is_checked_before_evidence() -> None:
    with pytest.raises(InvalidTransitionError):
        event_step(E.DRAFT, E.CONFIRMED, ADMIN, evidence=None)


def test_authorization_is_checked_before_evidence() -> None:
    with pytest.raises(NotAuthorizedError):
        event_step(E.SUBMITTED, E.CONFIRMED, ORGANIZER, evidence=None)


# ---- demotion on a schedule change ----------------------------------------------------


def test_changing_the_time_or_venue_of_a_confirmed_event_demotes_it_to_submitted() -> None:
    assert demote_on_schedule_change(E.CONFIRMED) is E.SUBMITTED


@pytest.mark.parametrize("status", [s for s in EventStatus if s is not E.CONFIRMED])
def test_demotion_leaves_every_other_status_alone(status: EventStatus) -> None:
    assert demote_on_schedule_change(status) is status


def test_demotion_is_not_something_a_user_can_ask_for() -> None:
    with pytest.raises(InvalidTransitionError):
        event_step(E.CONFIRMED, E.SUBMITTED, ADMIN, EVIDENCE)


# ---- commitments ----------------------------------------------------------------------


def test_acknowledged_is_not_confirmed_without_a_verifier_and_evidence() -> None:
    with pytest.raises(NotAuthorizedError):
        commitment_step(C.ACKNOWLEDGED, C.CONFIRMED, ORGANIZER, EVIDENCE)
    with pytest.raises(EvidenceRequiredError):
        commitment_step(C.ACKNOWLEDGED, C.CONFIRMED, ADMIN, evidence=None)
    done = commitment_step(C.ACKNOWLEDGED, C.CONFIRMED, ADMIN, EVIDENCE)
    assert done.status is C.CONFIRMED
    assert done.verification is not None
    assert done.verification.verified_by == ADMIN.user_id


def test_a_commitment_cannot_be_confirmed_before_it_is_acknowledged() -> None:
    with pytest.raises(InvalidTransitionError):
        commitment_step(C.REQUESTED, C.CONFIRMED, ADMIN, EVIDENCE)


def test_organizer_progress_is_recorded_as_reported_not_verified() -> None:
    step = commitment_step(C.REQUESTED, C.ACKNOWLEDGED, ORGANIZER, evidence=None)
    assert step.status is C.ACKNOWLEDGED
    assert step.reported_by == ORGANIZER.user_id
    assert step.verification is None


def test_conditionally_confirmed_is_still_only_reported() -> None:
    step = commitment_step(C.ACKNOWLEDGED, C.CONDITIONALLY_CONFIRMED, ORGANIZER, evidence=None)
    assert step.verification is None
    assert step.reported_by == ORGANIZER.user_id


def test_closing_a_commitment_needs_a_club_admin() -> None:
    assert commitment_step(C.CONFIRMED, C.CLOSED, CLUB_ADMIN, None).status is C.CLOSED
    with pytest.raises(NotAuthorizedError):
        commitment_step(C.CONFIRMED, C.CLOSED, ORGANIZER, None)


def test_a_user_cannot_set_needs_revalidation() -> None:
    for current in CommitmentStatus:
        with pytest.raises(InvalidTransitionError):
            commitment_step(current, C.NEEDS_REVALIDATION)


@pytest.mark.parametrize("current", sorted(REVALIDATION_SOURCES))
def test_an_event_change_sends_live_commitments_back_for_revalidation(
    current: CommitmentStatus,
) -> None:
    assert mark_needs_revalidation(current) is C.NEEDS_REVALIDATION


@pytest.mark.parametrize("current", [C.DRAFT, C.CLOSED, C.NEEDS_REVALIDATION])
def test_revalidation_leaves_draft_closed_and_already_flagged_alone(
    current: CommitmentStatus,
) -> None:
    assert mark_needs_revalidation(current) is current


def test_a_confirmation_is_never_carried_forward_across_a_change() -> None:
    assert mark_needs_revalidation(C.CONFIRMED) is not C.CONFIRMED


# ---- laws -----------------------------------------------------------------------------

actors = st.builds(
    Actor,
    user_id=st.just(USER),
    campus_admin=st.booleans(),
    memberships=st.dictionaries(
        st.just(CLUB), st.sampled_from([Role.ORGANIZER, Role.CLUB_ADMIN]), max_size=1
    ),
    via_agent=st.booleans(),
)
evidences = st.one_of(st.none(), st.just(EVIDENCE))
LAW = settings(max_examples=400, deadline=None)


@LAW
@given(actors, st.sampled_from(list(EventStatus)), st.sampled_from(list(EventStatus)), evidences)
def test_an_event_only_becomes_confirmed_with_an_admin_verifier_and_evidence(
    actor: Actor, current: EventStatus, target: EventStatus, evidence: Evidence | None
) -> None:
    try:
        result = event_step(current, target, actor, evidence)
    except (InvalidTransitionError, NotAuthorizedError, EvidenceRequiredError):
        return
    assert (current, target) in EVENT_EDGES
    if result.status is E.CONFIRMED:
        assert actor.campus_admin is True
        assert actor.via_agent is False
        assert evidence is not None
        assert result.verification is not None
        assert result.verification.verified_by == actor.user_id
    else:
        assert result.verification is None


@LAW
@given(
    actors,
    st.sampled_from(list(CommitmentStatus)),
    st.sampled_from(list(CommitmentStatus)),
    evidences,
)
def test_a_commitment_only_becomes_confirmed_with_an_admin_verifier_and_evidence(
    actor: Actor, current: CommitmentStatus, target: CommitmentStatus, evidence: Evidence | None
) -> None:
    try:
        result = commitment_step(current, target, actor, evidence)
    except (InvalidTransitionError, NotAuthorizedError, EvidenceRequiredError):
        return
    assert (current, target) in COMMITMENT_EDGES
    if result.status is C.CONFIRMED:
        assert actor.campus_admin is True
        assert actor.via_agent is False
        assert evidence is not None
        assert result.verification is not None
    else:
        assert result.verification is None


def test_each_reachable_status_names_the_action_it_needs() -> None:
    assert {s: event_action_for(s) for s in EventStatus} == {
        E.DRAFT: None,
        E.PROPOSED: Action.PROPOSE_EVENT,
        E.SUBMITTED: Action.SUBMIT_EVENT,
        E.CONFIRMED: Action.CONFIRM_EVENT,
        E.REJECTED: Action.REJECT_EVENT,
        E.CANCELLED: Action.CANCEL_EVENT,
        E.COMPLETED: Action.COMPLETE_EVENT,
    }
