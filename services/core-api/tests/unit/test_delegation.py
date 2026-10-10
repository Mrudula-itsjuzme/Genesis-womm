"""Delegation use cases (spine AD-10, AD-21): who may be represented, and as whom a call runs."""

from datetime import datetime
from uuid import UUID, uuid4

import pytest

from app.clients.delegation import PyJwtDelegationService
from app.domain.authz import Actor
from app.domain.enums import Role
from app.domain.lifecycle import NotAuthorizedError
from app.services.delegation import DelegationService
from tests.fakes import InMemoryDatabase

KEY = "d" * 64


class CountingTokens(PyJwtDelegationService):
    def __init__(self) -> None:
        super().__init__(KEY)
        self.minted = 0

    def issue(self, user_id: UUID, request_id: str) -> tuple[str, datetime]:
        self.minted += 1
        return super().issue(user_id, request_id)


def service_for(*actors: Actor) -> tuple[DelegationService, InMemoryDatabase, CountingTokens]:
    db = InMemoryDatabase()
    db.state.actors.update({actor.user_id: actor for actor in actors})
    tokens = CountingTokens()
    return DelegationService(db.uow, tokens), db, tokens


def organizer(role: Role = Role.ORGANIZER) -> Actor:
    return Actor(user_id=uuid4(), campus_admin=False, memberships={uuid4(): role})


CAMPUS_ADMIN = Actor(user_id=uuid4(), campus_admin=True, memberships={})
STUDENT = Actor(user_id=uuid4(), campus_admin=False, memberships={})


@pytest.mark.parametrize(
    "actor",
    [organizer(Role.ORGANIZER), organizer(Role.CLUB_ADMIN), CAMPUS_ADMIN],
    ids=["organizer", "club admin", "campus admin"],
)
def test_organizer_class_users_can_be_represented_for_one_turn(actor: Actor) -> None:
    service, _, tokens = service_for(actor)

    issued = service.issue(actor, "req-1")

    assert tokens.verify(issued.token) == actor.user_id
    assert issued.expires_at > datetime.now(issued.expires_at.tzinfo)


def test_someone_with_no_organizer_role_cannot_mint_a_delegation() -> None:
    service, _, tokens = service_for(STUDENT)

    with pytest.raises(NotAuthorizedError):
        service.issue(STUDENT, "req-1")
    assert tokens.minted == 0


def test_a_delegated_principal_cannot_mint_another_delegation() -> None:
    delegated = Actor(user_id=uuid4(), campus_admin=True, memberships={}, via_agent=True)
    service, _, tokens = service_for(delegated)

    with pytest.raises(NotAuthorizedError):
        service.issue(delegated, "req-1")
    assert tokens.minted == 0


def test_a_token_resolves_to_the_user_as_the_database_describes_them_now() -> None:
    club = uuid4()
    actor = Actor(user_id=uuid4(), campus_admin=False, memberships={club: Role.ORGANIZER})
    service, db, _ = service_for(actor)
    issued = service.issue(actor, "req-1")

    resolved = service.resolve(issued.token)

    assert resolved is not None
    assert (resolved.user_id, resolved.memberships, resolved.via_agent) == (
        actor.user_id,
        {club: Role.ORGANIZER},
        True,
    )

    # Roles are read on every call, so a revoked membership takes effect before the token expires.
    db.state.actors[actor.user_id] = Actor(
        user_id=actor.user_id, campus_admin=False, memberships={}
    )
    revoked = service.resolve(issued.token)
    assert revoked is not None
    assert revoked.memberships == {}


def test_a_token_for_a_user_who_no_longer_exists_resolves_to_nobody() -> None:
    actor = organizer()
    service, db, _ = service_for(actor)
    issued = service.issue(actor, "req-1")
    del db.state.actors[actor.user_id]

    assert service.resolve(issued.token) is None


@pytest.mark.parametrize("token", ["", "garbage", "a.b.c"])
def test_a_token_core_did_not_mint_resolves_to_nobody(token: str) -> None:
    service, _, _ = service_for(organizer())
    assert service.resolve(token) is None
