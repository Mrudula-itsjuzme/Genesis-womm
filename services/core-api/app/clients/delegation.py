"""Delegation tokens for one Agent turn (spine AD-10).

Core mints one when a signed-in organizer talks to the assistant. The Agent forwards it
unmodified and never decodes it; Core verifies it on `/internal/v1` and trusts only `sub`.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from jwt import InvalidTokenError

DELEGATION_AUDIENCE = "agent-tools"
MAX_DELEGATION_LIFETIME = timedelta(seconds=120)
_ISSUER = "core"
_REQUIRED = ["exp", "iat", "iss", "aud", "sub"]


class InvalidDelegationTokenError(ValueError):
    pass


class PyJwtDelegationService:
    def __init__(self, key: str, *, lifetime: timedelta = MAX_DELEGATION_LIFETIME) -> None:
        if not timedelta(0) < lifetime <= MAX_DELEGATION_LIFETIME:
            raise ValueError(f"delegation lifetime must be within {MAX_DELEGATION_LIFETIME}")
        self._key = key
        self._lifetime = lifetime

    def issue(self, user_id: UUID, request_id: str) -> tuple[str, datetime]:
        now = datetime.now(UTC)
        expires_at = now + self._lifetime
        claims = {
            "iss": _ISSUER,
            "aud": DELEGATION_AUDIENCE,
            "sub": str(user_id),
            "req": request_id,
            "jti": str(uuid4()),
            "iat": now,
            "exp": expires_at,
        }
        return jwt.encode(claims, self._key, algorithm="HS256"), expires_at

    def verify(self, token: str) -> UUID:
        try:
            claims = jwt.decode(
                token,
                self._key,
                algorithms=["HS256"],
                issuer=_ISSUER,
                audience=DELEGATION_AUDIENCE,
                options={"require": _REQUIRED},
            )
            if claims["exp"] - claims["iat"] > MAX_DELEGATION_LIFETIME.total_seconds():
                raise InvalidDelegationTokenError("delegation token lives too long")
            return UUID(str(claims["sub"]))
        except (InvalidTokenError, KeyError, ValueError) as error:
            raise InvalidDelegationTokenError("invalid delegation token") from error
