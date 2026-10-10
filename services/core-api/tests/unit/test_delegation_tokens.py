"""Delegation tokens (spine AD-10): one user, one Agent turn, two minutes at most."""

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

import jwt
import pytest

from app.clients.delegation import (
    DELEGATION_AUDIENCE,
    MAX_DELEGATION_LIFETIME,
    InvalidDelegationTokenError,
    PyJwtDelegationService,
)
from app.clients.tokens import InvalidSessionTokenError, PyJwtTokenService

KEY = "d" * 64
SESSION_KEY = "s" * 40


def forged(claims: dict[str, Any], *, key: str = KEY, algorithm: str = "HS256") -> str:
    """A token Core did not mint, with whichever claims a test wants to prove are refused."""
    now = datetime.now(UTC)
    base: dict[str, Any] = {
        "iss": "core",
        "aud": DELEGATION_AUDIENCE,
        "sub": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(seconds=60),
    }
    return jwt.encode({**base, **claims}, key, algorithm=algorithm)


def test_a_minted_token_names_the_user_and_expires_within_two_minutes() -> None:
    service = PyJwtDelegationService(KEY)
    user_id = uuid4()

    token, expires_at = service.issue(user_id, "req-7")

    assert service.verify(token) == user_id
    claims = jwt.decode(token, KEY, algorithms=["HS256"], audience=DELEGATION_AUDIENCE)
    assert claims["iss"] == "core"
    assert claims["aud"] == "agent-tools"
    assert claims["req"] == "req-7"
    assert claims["jti"]
    assert timedelta(0) < expires_at - datetime.now(UTC) <= MAX_DELEGATION_LIFETIME
    assert claims["exp"] - claims["iat"] <= MAX_DELEGATION_LIFETIME.total_seconds()


def test_every_token_has_its_own_id() -> None:
    service = PyJwtDelegationService(KEY)
    user_id = uuid4()
    first, _ = service.issue(user_id, "req-1")
    second, _ = service.issue(user_id, "req-1")
    ids = {
        jwt.decode(token, KEY, algorithms=["HS256"], audience="agent-tools")["jti"]
        for token in (first, second)
    }
    assert len(ids) == 2


@pytest.mark.parametrize("lifetime", [timedelta(0), timedelta(seconds=-5), timedelta(seconds=121)])
def test_a_lifetime_beyond_two_minutes_cannot_be_configured(lifetime: timedelta) -> None:
    with pytest.raises(ValueError, match="lifetime"):
        PyJwtDelegationService(KEY, lifetime=lifetime)


def test_the_longest_allowed_lifetime_is_exactly_two_minutes() -> None:
    assert timedelta(seconds=120) == MAX_DELEGATION_LIFETIME
    PyJwtDelegationService(KEY, lifetime=MAX_DELEGATION_LIFETIME)


@pytest.mark.parametrize(
    "token",
    [
        pytest.param(forged({}, key="x" * 40), id="signed with another key"),
        pytest.param(forged({"aud": "somewhere-else"}), id="wrong audience"),
        pytest.param(forged({"iss": "agent"}), id="wrong issuer"),
        pytest.param(forged({"exp": datetime.now(UTC) - timedelta(seconds=5)}), id="expired"),
        pytest.param(forged({"sub": "not-a-uuid"}), id="subject is not a user id"),
        pytest.param(forged({}, algorithm="HS512"), id="another HMAC algorithm"),
        pytest.param(forged({}, key="", algorithm="none"), id="unsigned (alg none)"),
        pytest.param("not.a.jwt", id="garbage"),
        pytest.param("", id="empty"),
    ],
)
def test_a_token_core_did_not_mint_is_refused(token: str) -> None:
    with pytest.raises(InvalidDelegationTokenError):
        PyJwtDelegationService(KEY).verify(token)


@pytest.mark.parametrize("missing", ["exp", "aud", "iss", "sub"])
def test_a_token_missing_a_required_claim_is_refused(missing: str) -> None:
    now = datetime.now(UTC)
    claims = {
        "iss": "core",
        "aud": DELEGATION_AUDIENCE,
        "sub": str(uuid4()),
        "iat": now,
        "exp": now + timedelta(seconds=60),
    }
    del claims[missing]
    token = jwt.encode(claims, KEY, algorithm="HS256")
    with pytest.raises(InvalidDelegationTokenError):
        PyJwtDelegationService(KEY).verify(token)


def test_a_token_that_never_expires_is_refused() -> None:
    # A far-future exp is still a token Core would never mint: lifetime is capped at two minutes.
    now = datetime.now(UTC)
    token = forged({"iat": now, "exp": now + timedelta(days=365)})
    with pytest.raises(InvalidDelegationTokenError):
        PyJwtDelegationService(KEY).verify(token)


def test_only_the_subject_is_trusted() -> None:
    """Claims such as a role or a club are ignored: authority comes from the database."""
    user_id = uuid4()
    token = forged({"sub": str(user_id), "role": "CAMPUS_ADMIN", "campus_admin": True})
    assert PyJwtDelegationService(KEY).verify(token) == user_id


def test_a_session_token_is_not_a_delegation_and_a_delegation_is_not_a_session() -> None:
    user_id = uuid4()
    delegation, _ = PyJwtDelegationService(KEY).issue(user_id, "req-1")
    session, _ = PyJwtTokenService(SESSION_KEY).issue(user_id)

    with pytest.raises(InvalidDelegationTokenError):
        PyJwtDelegationService(KEY).verify(session)
    with pytest.raises(InvalidSessionTokenError):
        PyJwtTokenService(SESSION_KEY).verify(delegation)
    # Even sharing one key (which settings forbid), the audience keeps them apart.
    with pytest.raises(InvalidSessionTokenError):
        PyJwtTokenService(KEY).verify(delegation)
