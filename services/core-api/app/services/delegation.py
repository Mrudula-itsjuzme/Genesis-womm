"""Delegation for one Agent turn (spine AD-10, AD-21).

A signed-in organizer-class user may be represented by the Agent for a couple of minutes. The
token only names the user; what the Agent can do is decided from the database on every call.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from app.domain.authz import Action, Actor, Resource, authorize
from app.domain.lifecycle import NotAuthorizedError
from app.services.ports import DelegationTokenService, DirectoryUnitOfWork


@dataclass(frozen=True)
class IssuedDelegation:
    token: str = field(repr=False)
    expires_at: datetime


class DelegationService:
    def __init__(
        self, uow_factory: Callable[[], DirectoryUnitOfWork], tokens: DelegationTokenService
    ) -> None:
        self._uow_factory = uow_factory
        self._tokens = tokens

    def issue(self, actor: Actor, request_id: str) -> IssuedDelegation:
        decision = authorize(actor, Action.ISSUE_DELEGATION, Resource())
        if not decision.allowed:
            raise NotAuthorizedError(decision)
        token, expires_at = self._tokens.issue(actor.user_id, request_id)
        return IssuedDelegation(token=token, expires_at=expires_at)

    def resolve(self, token: str) -> Actor | None:
        """The delegated user as the database describes them now, or None for any bad token."""
        try:
            user_id = self._tokens.verify(token)
        except ValueError:
            return None
        with self._uow_factory() as uow:
            return uow.actors.load_actor(user_id, via_agent=True)
