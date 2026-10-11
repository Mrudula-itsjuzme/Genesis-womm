from datetime import timedelta
from uuid import uuid4

import jwt
import pytest

from app.clients.tokens import InvalidSessionTokenError, PyJwtTokenService


def test_session_token_round_trip_and_rejects_wrong_issuer() -> None:
    service = PyJwtTokenService("s" * 40, lifetime=timedelta(hours=1))
    user_id = uuid4()
    token, _ = service.issue(user_id)
    assert service.verify(token) == user_id

    wrong_issuer = jwt.encode({"iss": "agent", "sub": str(user_id)}, "s" * 40, algorithm="HS256")
    with pytest.raises(InvalidSessionTokenError):
        service.verify(wrong_issuer)


def test_session_token_rejects_a_tampered_signature() -> None:
    service = PyJwtTokenService("s" * 40)
    token, _ = service.issue(uuid4())
    with pytest.raises(InvalidSessionTokenError):
        service.verify(f"{token}x")


def test_session_token_requires_an_expiry_claim() -> None:
    service = PyJwtTokenService("s" * 40)
    token = jwt.encode({"iss": "core", "sub": str(uuid4())}, "s" * 40, algorithm="HS256")

    with pytest.raises(InvalidSessionTokenError):
        service.verify(token)
