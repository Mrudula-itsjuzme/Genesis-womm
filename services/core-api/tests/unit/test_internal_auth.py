"""The two credentials the Agent facade requires (spine AD-10, AD-19).

`X-Internal-Key` proves the caller is the Agent service; the delegation bearer says which user
it speaks for. Both are checked on every call, the key first.
"""

from typing import Annotated
from uuid import uuid4

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import require_delegated_actor, require_internal_key
from app.api.errors import install_error_handlers
from app.api.middleware import RequestIdMiddleware
from app.clients.delegation import PyJwtDelegationService
from app.clients.tokens import PyJwtTokenService
from app.domain.authz import Actor
from app.domain.enums import Role
from app.services.delegation import DelegationService
from tests.fakes import InMemoryDatabase

INTERNAL_KEY = "i" * 40
DELEGATION_KEY = "d" * 64
SESSION_KEY = "s" * 64
CLUB = uuid4()
ORGANIZER = Actor(user_id=uuid4(), campus_admin=False, memberships={CLUB: Role.ORGANIZER})


def build(internal_key: str | None = INTERNAL_KEY) -> tuple[TestClient, InMemoryDatabase]:
    db = InMemoryDatabase()
    db.state.actors[ORGANIZER.user_id] = ORGANIZER
    app = FastAPI()
    app.state.delegation = DelegationService(db.uow, PyJwtDelegationService(DELEGATION_KEY))
    if internal_key is not None:
        app.state.internal_api_key = internal_key
    app.add_middleware(RequestIdMiddleware)
    install_error_handlers(app)

    @app.get("/probe", dependencies=[Depends(require_internal_key)])
    def probe(actor: Annotated[Actor, Depends(require_delegated_actor)]) -> dict[str, object]:
        return {"user": str(actor.user_id), "via_agent": actor.via_agent}

    return TestClient(app, raise_server_exceptions=False), db


def delegation_for(actor: Actor = ORGANIZER) -> str:
    token, _ = PyJwtDelegationService(DELEGATION_KEY).issue(actor.user_id, "req-1")
    return token


def headers(key: str | None = INTERNAL_KEY, bearer: str | None = None) -> dict[str, str]:
    sent: dict[str, str] = {}
    if key is not None:
        sent["X-Internal-Key"] = key
    if bearer is not None:
        sent["Authorization"] = f"Bearer {bearer}"
    return sent


def test_both_credentials_present_runs_the_call_as_the_delegated_user() -> None:
    client, _ = build()

    response = client.get("/probe", headers=headers(bearer=delegation_for()))

    assert response.status_code == 200
    assert response.json() == {"user": str(ORGANIZER.user_id), "via_agent": True}


@pytest.mark.parametrize("key", [None, "", "wrong", "i" * 39, "i" * 41, INTERNAL_KEY + " "])
def test_a_missing_or_wrong_internal_key_is_unauthenticated(key: str | None) -> None:
    client, db = build()

    response = client.get("/probe", headers=headers(key=key, bearer=delegation_for()))

    assert response.status_code == 401
    body = response.json()
    assert body["code"] == "UNAUTHENTICATED"
    assert body["request_id"]
    assert db.log == [], "the database must not be touched before the key is accepted"


def test_a_non_ascii_internal_key_is_refused_not_a_server_error() -> None:
    client, _ = build()
    response = client.get(
        "/probe",
        headers={
            b"X-Internal-Key": "café".encode("latin-1"),
            b"Authorization": f"Bearer {delegation_for()}".encode(),
        },
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "bearer",
    [None, "", "garbage", PyJwtTokenService(SESSION_KEY).issue(ORGANIZER.user_id)[0]],
    ids=["absent", "empty", "garbage", "a session token"],
)
def test_a_missing_or_wrong_delegation_token_is_unauthenticated(bearer: str | None) -> None:
    client, _ = build()

    response = client.get("/probe", headers=headers(bearer=bearer))

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"


def test_a_delegation_for_a_user_who_is_gone_is_unauthenticated() -> None:
    client, db = build()
    token = delegation_for()
    del db.state.actors[ORGANIZER.user_id]

    assert client.get("/probe", headers=headers(bearer=token)).status_code == 401


def test_the_failure_message_does_not_say_which_credential_was_wrong() -> None:
    client, _ = build()
    bad_key = client.get("/probe", headers=headers(key="nope", bearer=delegation_for())).json()
    bad_token = client.get("/probe", headers=headers(bearer="nope")).json()
    assert bad_key["message"] == bad_token["message"]


def test_with_no_key_configured_only_the_delegation_is_required() -> None:
    """Local development: settings allow an empty key only when APP_ENV is local."""
    client, _ = build(internal_key="")

    assert (
        client.get("/probe", headers=headers(key=None, bearer=delegation_for())).status_code == 200
    )
    assert client.get("/probe", headers=headers(key=None)).status_code == 401


def test_a_facade_with_no_key_configured_fails_closed_instead_of_open() -> None:
    client, _ = build(internal_key=None)

    response = client.get("/probe", headers=headers(key=INTERNAL_KEY, bearer=delegation_for()))

    assert response.status_code == 500
    assert response.json()["code"] == "INTERNAL_ERROR"
