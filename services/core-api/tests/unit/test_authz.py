"""The single authorization decision point (spine AD-21, AD-10, AD-6, AD-9)."""

from dataclasses import replace
from uuid import UUID

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.domain.authz import (
    AGENT_ACTIONS,
    Action,
    Actor,
    Decision,
    Reason,
    Resource,
    Visibility,
    authorize,
)
from app.domain.enums import Role

CLUB_A, CLUB_B = UUID(int=1001), UUID(int=1002)
USER = UUID(int=1)
OTHER_USER = UUID(int=2)

ADMIN_ONLY = {
    Action.CONFIRM_EVENT,
    Action.REJECT_EVENT,
    Action.CREATE_OVERRIDE,
    Action.VERIFY_COMMITMENT,
}
CLUB_ADMIN_ONLY = {
    Action.CANCEL_EVENT,
    Action.COMPLETE_EVENT,
    Action.APPLY_CHANGE,
    Action.CLOSE_COMMITMENT,
}
ORGANIZER_OWN_CLUB = {
    Action.CREATE_EVENT,
    Action.EDIT_EVENT,
    Action.PROPOSE_EVENT,
    Action.SUBMIT_EVENT,
    Action.CHECK_CONFLICTS,
    Action.REQUEST_CHANGE,
    Action.REPORT_COMMITMENT,
    Action.FILE_AGENT_ACTION,
}
OWNER_SCOPED = {Action.CONFIRM_AGENT_ACTION}
ANY_ORGANIZER = {Action.VIEW_EVENT, Action.ISSUE_DELEGATION}


def admin() -> Actor:
    return Actor(user_id=USER, campus_admin=True)


def club_admin(club: UUID = CLUB_A) -> Actor:
    return Actor(user_id=USER, memberships={club: Role.CLUB_ADMIN})


def organizer(club: UUID = CLUB_A) -> Actor:
    return Actor(user_id=USER, memberships={club: Role.ORGANIZER})


# A student is simply someone with no campus role and no club membership.
STUDENT = OUTSIDER = Actor(user_id=USER)


def ctx(club: UUID | None = CLUB_A, owner: UUID | None = USER) -> Resource:
    return Resource(club_id=club, owner_id=owner)


def allowed(actor: Actor, action: Action, resource: Resource | None = None) -> bool:
    return authorize(actor, action, resource or ctx()).allowed


def granted(actor: Actor, resource: Resource | None = None) -> set[Action]:
    return {a for a in Action if allowed(actor, a, resource)}


# ---- the matrix -----------------------------------------------------------------------


def test_a_campus_admin_can_do_everything_for_any_club() -> None:
    for club in (CLUB_A, CLUB_B):
        assert granted(admin(), ctx(club)) == set(Action)


def test_a_club_admin_runs_their_own_club_but_confirms_nothing() -> None:
    expected = ORGANIZER_OWN_CLUB | CLUB_ADMIN_ONLY | OWNER_SCOPED | ANY_ORGANIZER
    assert granted(club_admin()) == expected
    assert not expected & ADMIN_ONLY


def test_an_organizer_cannot_cancel_complete_apply_changes_or_close_commitments() -> None:
    expected = ORGANIZER_OWN_CLUB | OWNER_SCOPED | ANY_ORGANIZER
    assert granted(organizer()) == expected
    assert not expected & (CLUB_ADMIN_ONLY | ADMIN_ONLY)


@pytest.mark.parametrize("actor", [club_admin(CLUB_B), organizer(CLUB_B)])
def test_membership_of_another_club_grants_only_what_needs_no_club(actor: Actor) -> None:
    # Viewing (as a summary), minting a delegation, and owning one's own agent actions.
    assert granted(actor) == ANY_ORGANIZER | OWNER_SCOPED


@pytest.mark.parametrize("actor", [STUDENT, OUTSIDER])
def test_a_student_or_stranger_is_denied_every_organizer_action(actor: Actor) -> None:
    for club in (CLUB_A, CLUB_B):
        assert granted(actor, ctx(club)) == set()


# ---- confirmation and overrides -------------------------------------------------------


@pytest.mark.parametrize("action", sorted(ADMIN_ONLY))
def test_only_a_campus_admin_may_confirm_reject_override_or_verify(action: Action) -> None:
    for actor in (club_admin(), organizer(), STUDENT, OUTSIDER):
        decision = authorize(actor, action, ctx())
        assert decision.allowed is False
        assert decision.reason in {Reason.NOT_CAMPUS_ADMIN}
    assert allowed(admin(), action)


def test_a_club_admin_of_the_event_still_cannot_confirm_it() -> None:
    assert authorize(club_admin(CLUB_A), Action.CONFIRM_EVENT, ctx(CLUB_A)).allowed is False


# ---- the delegated agent --------------------------------------------------------------


def test_the_agent_may_only_view_check_conflicts_and_file_proposals() -> None:
    assert (
        frozenset({Action.VIEW_EVENT, Action.CHECK_CONFLICTS, Action.FILE_AGENT_ACTION})
        == AGENT_ACTIONS
    )


@pytest.mark.parametrize("human", [admin(), club_admin(), organizer()])
def test_a_delegated_principal_gets_exactly_the_agent_actions_the_human_has(human: Actor) -> None:
    delegated = replace(human, via_agent=True)
    assert granted(delegated) == granted(human) & AGENT_ACTIONS


@pytest.mark.parametrize(
    "action",
    [
        Action.CONFIRM_EVENT,
        Action.CREATE_OVERRIDE,
        Action.CONFIRM_AGENT_ACTION,
        Action.ISSUE_DELEGATION,
        Action.REJECT_EVENT,
        Action.APPLY_CHANGE,
        Action.EDIT_EVENT,
        Action.CREATE_EVENT,
    ],
)
def test_an_agent_acting_for_a_campus_admin_still_cannot_do_this(action: Action) -> None:
    decision = authorize(replace(admin(), via_agent=True), action, ctx())
    assert decision.allowed is False
    assert decision.reason is Reason.AGENT_NOT_ALLOWED


def test_the_agent_cannot_mint_another_delegation() -> None:
    assert allowed(replace(organizer(), via_agent=True), Action.ISSUE_DELEGATION) is False


# ---- visibility -----------------------------------------------------------------------


def test_own_club_and_campus_admins_see_full_detail_others_see_a_summary() -> None:
    assert (
        authorize(organizer(CLUB_A), Action.VIEW_EVENT, ctx(CLUB_A)).visibility is Visibility.FULL
    )
    assert authorize(admin(), Action.VIEW_EVENT, ctx(CLUB_B)).visibility is Visibility.FULL
    other = authorize(organizer(CLUB_A), Action.VIEW_EVENT, ctx(CLUB_B))
    assert other.allowed is True
    assert other.visibility is Visibility.SUMMARY


def test_viewing_without_a_club_is_a_summary_unless_admin() -> None:
    assert authorize(organizer(), Action.VIEW_EVENT, Resource()).visibility is Visibility.SUMMARY
    assert authorize(admin(), Action.VIEW_EVENT, Resource()).visibility is Visibility.FULL


def test_only_allowed_view_decisions_carry_a_visibility() -> None:
    denied = authorize(STUDENT, Action.VIEW_EVENT, ctx())
    assert denied.allowed is False
    assert denied.visibility is None


# ---- ownership ------------------------------------------------------------------------


def test_only_the_owner_confirms_an_agent_action_and_not_even_an_admin_for_someone_else() -> None:
    mine = ctx(owner=USER)
    theirs = ctx(owner=OTHER_USER)
    assert allowed(organizer(), Action.CONFIRM_AGENT_ACTION, mine)
    assert authorize(organizer(), Action.CONFIRM_AGENT_ACTION, theirs).reason is Reason.NOT_OWNER
    assert authorize(admin(), Action.CONFIRM_AGENT_ACTION, theirs).reason is Reason.NOT_OWNER


def test_a_student_cannot_confirm_even_an_action_that_names_them() -> None:
    assert allowed(STUDENT, Action.CONFIRM_AGENT_ACTION, ctx(owner=USER)) is False


# ---- shape and misuse -----------------------------------------------------------------


@pytest.mark.parametrize("action", sorted(ORGANIZER_OWN_CLUB | CLUB_ADMIN_ONLY))
def test_a_club_scoped_action_without_a_club_is_a_programming_error(action: Action) -> None:
    with pytest.raises(ValueError, match="club_id"):
        authorize(admin(), action, Resource())


@pytest.mark.parametrize("action", sorted(ADMIN_ONLY))
def test_campus_wide_actions_need_no_club(action: Action) -> None:
    # An override pairs two events that may belong to different clubs.
    assert authorize(admin(), action, Resource()).allowed is True


def test_decisions_always_carry_a_reason() -> None:
    assert authorize(admin(), Action.CONFIRM_EVENT, ctx()) == Decision(
        allowed=True, reason=Reason.ALLOWED, visibility=None
    )
    for decision in (
        authorize(STUDENT, Action.CREATE_EVENT, ctx()),
        authorize(organizer(), Action.CONFIRM_EVENT, ctx()),
        authorize(organizer(CLUB_B), Action.EDIT_EVENT, ctx(CLUB_A)),
    ):
        assert decision.allowed is False
        assert decision.reason is not Reason.ALLOWED


def test_memberships_can_only_be_organizer_or_club_admin() -> None:
    for bad in (Role.CAMPUS_ADMIN, Role.STUDENT):
        with pytest.raises(ValueError, match="membership"):
            Actor(user_id=USER, memberships={CLUB_A: bad})


def test_an_actor_carries_no_free_form_role_string() -> None:
    # Roles are derived from database rows into these typed fields; there is nowhere to put a
    # client-supplied "role" or "authorized_by" (spine AD-21).
    assert set(Actor.__dataclass_fields__) == {
        "user_id",
        "campus_admin",
        "memberships",
        "via_agent",
    }


# ---- laws for every actor -------------------------------------------------------------

actors = st.builds(
    Actor,
    user_id=st.sampled_from([USER, OTHER_USER]),
    campus_admin=st.booleans(),
    memberships=st.dictionaries(
        st.sampled_from([CLUB_A, CLUB_B]), st.sampled_from([Role.ORGANIZER, Role.CLUB_ADMIN])
    ),
    via_agent=st.booleans(),
)
resources = st.builds(
    Resource,
    club_id=st.sampled_from([CLUB_A, CLUB_B]),
    owner_id=st.sampled_from([USER, OTHER_USER]),
)
LAW = settings(max_examples=400, deadline=None)


@LAW
@given(actors, st.sampled_from(list(Action)), resources)
def test_delegation_never_widens_what_a_human_may_do(
    actor: Actor, action: Action, resource: Resource
) -> None:
    human = replace(actor, via_agent=False)
    delegated = replace(actor, via_agent=True)
    if authorize(delegated, action, resource).allowed:
        assert authorize(human, action, resource).allowed
        assert action in AGENT_ACTIONS


@LAW
@given(actors, resources)
def test_only_a_campus_admin_ever_confirms_overrides_rejects_or_verifies(
    actor: Actor, resource: Resource
) -> None:
    for action in ADMIN_ONLY:
        if authorize(actor, action, resource).allowed:
            assert actor.campus_admin is True
            assert actor.via_agent is False


@LAW
@given(actors, st.sampled_from(list(Action)), resources)
def test_someone_with_no_campus_role_and_no_membership_is_always_denied(
    actor: Actor, action: Action, resource: Resource
) -> None:
    nobody = replace(actor, campus_admin=False, memberships={})
    assert authorize(nobody, action, resource).allowed is False


@LAW
@given(actors, st.sampled_from(list(Action)), resources)
def test_a_campus_admin_acts_for_any_club_and_adding_rights_never_removes_any(
    actor: Actor, action: Action, resource: Resource
) -> None:
    base = authorize(actor, action, resource)
    promoted = authorize(replace(actor, campus_admin=True), action, resource)
    if base.allowed:
        assert promoted.allowed
