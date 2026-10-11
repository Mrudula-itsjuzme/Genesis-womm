"""The composition root hands the facade the right keys and keeps the two token kinds apart."""

from collections.abc import Iterator
from uuid import uuid4

import pytest
from pydantic import SecretStr

from app.clients.delegation import InvalidDelegationTokenError, PyJwtDelegationService
from app.container import Container, build_container
from app.domain.authz import Actor
from app.domain.enums import Role
from app.main import create_app
from app.services.readiness import ReadinessService
from app.settings import Settings
from tests.fakes import FakeReadinessProbe, make_settings

SESSION_KEY = "s" * 40
DELEGATION_KEY = "d" * 40
INTERNAL_KEY = "i" * 40
ORGANIZER = Actor(user_id=uuid4(), campus_admin=False, memberships={uuid4(): Role.ORGANIZER})


def settings_with_keys() -> Settings:
    return make_settings(
        session_signing_key=SecretStr(SESSION_KEY),
        delegation_signing_key=SecretStr(DELEGATION_KEY),
        internal_api_key=SecretStr(INTERNAL_KEY),
    )


@pytest.fixture
def container() -> Iterator[Container]:
    built = build_container(settings_with_keys())
    yield built
    built.dispose()


def test_delegations_are_signed_with_the_delegation_key_and_not_the_session_key(
    container: Container,
) -> None:
    assert container.delegation is not None

    issued = container.delegation.issue(ORGANIZER, "req-1")

    assert PyJwtDelegationService(DELEGATION_KEY).verify(issued.token) == ORGANIZER.user_id
    with pytest.raises(InvalidDelegationTokenError):
        PyJwtDelegationService(SESSION_KEY).verify(issued.token)


def test_the_app_publishes_the_delegation_service_and_the_internal_key(
    container: Container,
) -> None:
    app = create_app(settings_with_keys(), container)

    assert app.state.delegation is container.delegation
    assert app.state.internal_api_key == INTERNAL_KEY


def test_a_container_without_a_key_publishes_none_so_the_facade_fails_closed() -> None:
    bare = Container(readiness=ReadinessService(FakeReadinessProbe(), "0001"))

    app = create_app(settings_with_keys(), bare)

    assert not hasattr(app.state, "internal_api_key")


def test_the_app_publishes_the_agent_action_service(container: Container) -> None:
    assert container.agent_actions is not None

    app = create_app(settings_with_keys(), container)

    assert app.state.agent_actions is container.agent_actions


def test_change_queries_are_wired_to_the_app(container: Container) -> None:
    assert container.changes is not None
    app = create_app(settings_with_keys(), container)
    assert app.state.changes is container.changes
