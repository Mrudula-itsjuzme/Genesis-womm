"""The single authorization decision point (spine AD-21, AD-10, AD-6, AD-9).

``authorize`` is the only place roles are interpreted. Routes and services call it; nothing
else decides who may do what. It is pure: the ``Actor`` is built from database rows for this
request, so a role or ``authorized_by`` supplied by a client has nowhere to enter.

Until stakeholders decide otherwise (PLAN open decision 3), only a CAMPUS_ADMIN may confirm an
event, reject it, create an override or verify a commitment. Widening that is a change to the
rule table below and nothing else.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID

from app.domain.enums import Role


class Action(StrEnum):
    CREATE_EVENT = "CREATE_EVENT"
    VIEW_EVENT = "VIEW_EVENT"
    EDIT_EVENT = "EDIT_EVENT"
    PROPOSE_EVENT = "PROPOSE_EVENT"
    SUBMIT_EVENT = "SUBMIT_EVENT"
    CANCEL_EVENT = "CANCEL_EVENT"
    COMPLETE_EVENT = "COMPLETE_EVENT"
    CONFIRM_EVENT = "CONFIRM_EVENT"
    REJECT_EVENT = "REJECT_EVENT"
    CHECK_CONFLICTS = "CHECK_CONFLICTS"
    CREATE_OVERRIDE = "CREATE_OVERRIDE"
    REQUEST_CHANGE = "REQUEST_CHANGE"
    APPLY_CHANGE = "APPLY_CHANGE"
    REPORT_COMMITMENT = "REPORT_COMMITMENT"
    VERIFY_COMMITMENT = "VERIFY_COMMITMENT"
    CLOSE_COMMITMENT = "CLOSE_COMMITMENT"
    FILE_AGENT_ACTION = "FILE_AGENT_ACTION"
    CONFIRM_AGENT_ACTION = "CONFIRM_AGENT_ACTION"
    ISSUE_DELEGATION = "ISSUE_DELEGATION"
    SUBMIT_PROPOSAL = "SUBMIT_PROPOSAL"
    VIEW_PROPOSAL = "VIEW_PROPOSAL"
    REVIEW_PROPOSAL = "REVIEW_PROPOSAL"


class Visibility(StrEnum):
    FULL = "FULL"
    SUMMARY = "SUMMARY"


class Reason(StrEnum):
    ALLOWED = "ALLOWED"
    NOT_ORGANIZER = "NOT_ORGANIZER"
    NOT_IN_CLUB = "NOT_IN_CLUB"
    NOT_CLUB_ADMIN = "NOT_CLUB_ADMIN"
    NOT_FACULTY_ADVISOR = "NOT_FACULTY_ADVISOR"
    NOT_CAMPUS_ADMIN = "NOT_CAMPUS_ADMIN"
    NOT_OWNER = "NOT_OWNER"
    AGENT_NOT_ALLOWED = "AGENT_NOT_ALLOWED"


class _Scope(StrEnum):
    ANY_ORGANIZER = "ANY_ORGANIZER"  # any organizer-class user; no club needed
    OWN_CLUB_ORGANIZER = "OWN_CLUB_ORGANIZER"  # ORGANIZER, CLUB_ADMIN, or FACULTY_ADVISOR of the resource's club
    OWN_CLUB_ADMIN = "OWN_CLUB_ADMIN"  # CLUB_ADMIN of the resource's club
    OWN_FACULTY_ADVISOR = "OWN_FACULTY_ADVISOR"  # FACULTY_ADVISOR of the resource's club
    REVIEW_PROPOSAL = "REVIEW_PROPOSAL"  # CAMPUS_ADMIN or FACULTY_ADVISOR of the resource's club
    CAMPUS_ADMIN = "CAMPUS_ADMIN"  # campus-wide
    ACTION_OWNER = "ACTION_OWNER"  # the human a proposal was filed for


# The rule table. Reading this is reading the policy.
_SCOPE: dict[Action, _Scope] = {
    Action.CREATE_EVENT: _Scope.OWN_CLUB_ORGANIZER,
    Action.VIEW_EVENT: _Scope.ANY_ORGANIZER,
    Action.EDIT_EVENT: _Scope.OWN_CLUB_ORGANIZER,
    Action.PROPOSE_EVENT: _Scope.OWN_CLUB_ORGANIZER,
    Action.SUBMIT_EVENT: _Scope.OWN_CLUB_ORGANIZER,
    Action.CANCEL_EVENT: _Scope.OWN_CLUB_ADMIN,
    Action.COMPLETE_EVENT: _Scope.OWN_CLUB_ADMIN,
    Action.CONFIRM_EVENT: _Scope.CAMPUS_ADMIN,
    Action.REJECT_EVENT: _Scope.CAMPUS_ADMIN,
    Action.CHECK_CONFLICTS: _Scope.OWN_CLUB_ORGANIZER,
    Action.CREATE_OVERRIDE: _Scope.CAMPUS_ADMIN,
    Action.REQUEST_CHANGE: _Scope.OWN_CLUB_ORGANIZER,
    Action.APPLY_CHANGE: _Scope.OWN_CLUB_ADMIN,
    Action.REPORT_COMMITMENT: _Scope.OWN_CLUB_ORGANIZER,
    Action.VERIFY_COMMITMENT: _Scope.CAMPUS_ADMIN,
    Action.CLOSE_COMMITMENT: _Scope.OWN_CLUB_ADMIN,
    Action.FILE_AGENT_ACTION: _Scope.OWN_CLUB_ORGANIZER,
    Action.CONFIRM_AGENT_ACTION: _Scope.ACTION_OWNER,
    Action.ISSUE_DELEGATION: _Scope.ANY_ORGANIZER,
    # An event's proposal document: the club submits and reads it; faculty advisors and campus admins review it.
    Action.SUBMIT_PROPOSAL: _Scope.OWN_CLUB_ORGANIZER,
    Action.VIEW_PROPOSAL: _Scope.OWN_CLUB_ORGANIZER,
    Action.REVIEW_PROPOSAL: _Scope.REVIEW_PROPOSAL,
}

# A delegated (agent) principal can read, check conflicts and file proposals. It can never
# confirm, override, apply, mint a delegation or confirm a proposal.
AGENT_ACTIONS: frozenset[Action] = frozenset(
    {Action.VIEW_EVENT, Action.CHECK_CONFLICTS, Action.FILE_AGENT_ACTION}
)

_CLUB_SCOPES = frozenset(
    {_Scope.OWN_CLUB_ORGANIZER, _Scope.OWN_CLUB_ADMIN, _Scope.OWN_FACULTY_ADVISOR, _Scope.REVIEW_PROPOSAL}
)
_MEMBERSHIP_ROLES = frozenset({Role.ORGANIZER, Role.CLUB_ADMIN, Role.FACULTY_ADVISOR})


@dataclass(frozen=True)
class Actor:
    """Who is acting, derived from database rows for this request."""

    user_id: UUID
    campus_admin: bool = False
    memberships: Mapping[UUID, Role] = field(default_factory=dict)  # club_id -> role
    via_agent: bool = False  # acting through a delegation token

    def __post_init__(self) -> None:
        for role in self.memberships.values():
            if role not in _MEMBERSHIP_ROLES:
                raise ValueError(
                    f"a membership role must be ORGANIZER, CLUB_ADMIN, or FACULTY_ADVISOR, not {role}"
                )

    @property
    def organizer_class(self) -> bool:
        return self.campus_admin or bool(self.memberships)


@dataclass(frozen=True)
class Resource:
    club_id: UUID | None = None
    owner_id: UUID | None = None  # for proposals: the human they were filed for


@dataclass(frozen=True)
class Decision:
    allowed: bool
    reason: Reason
    visibility: Visibility | None = None  # only set for allowed VIEW_EVENT decisions


def _deny(reason: Reason) -> Decision:
    return Decision(allowed=False, reason=reason)


def _allow(visibility: Visibility | None = None) -> Decision:
    return Decision(allowed=True, reason=Reason.ALLOWED, visibility=visibility)


def authorize(actor: Actor, action: Action, resource: Resource | None = None) -> Decision:
    resource = resource or Resource()
    scope = _SCOPE[action]

    if scope in _CLUB_SCOPES and resource.club_id is None:
        # A missing club is a bug in the caller, not a reason to guess an answer.
        raise ValueError(f"club_id is required to authorize {action}")

    if actor.via_agent and action not in AGENT_ACTIONS:
        return _deny(Reason.AGENT_NOT_ALLOWED)

    if scope is _Scope.CAMPUS_ADMIN:
        return _allow() if actor.campus_admin else _deny(Reason.NOT_CAMPUS_ADMIN)

    if not actor.organizer_class:
        return _deny(Reason.NOT_ORGANIZER)

    if scope is _Scope.ANY_ORGANIZER:
        if action is Action.VIEW_EVENT:
            own_club = resource.club_id in actor.memberships
            full = actor.campus_admin or own_club
            return _allow(Visibility.FULL if full else Visibility.SUMMARY)
        return _allow()

    if scope is _Scope.ACTION_OWNER:
        owned = resource.owner_id is not None and resource.owner_id == actor.user_id
        return _allow() if owned else _deny(Reason.NOT_OWNER)

    # Club-scoped actions. A campus admin acts for any club.
    if actor.campus_admin:
        return _allow()
    role = actor.memberships.get(resource.club_id) if resource.club_id else None
    if role is None:
        return _deny(Reason.NOT_IN_CLUB)
    if scope is _Scope.OWN_CLUB_ADMIN and role is not Role.CLUB_ADMIN:
        return _deny(Reason.NOT_CLUB_ADMIN)
    if scope is _Scope.OWN_FACULTY_ADVISOR and role is not Role.FACULTY_ADVISOR:
        return _deny(Reason.NOT_FACULTY_ADVISOR)
    if scope is _Scope.REVIEW_PROPOSAL and role is not Role.FACULTY_ADVISOR:
        return _deny(Reason.NOT_FACULTY_ADVISOR)
    return _allow()
