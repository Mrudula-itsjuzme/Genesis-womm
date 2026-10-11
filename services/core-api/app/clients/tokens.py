from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from jwt import InvalidTokenError


class InvalidSessionTokenError(ValueError):
    pass


class PyJwtTokenService:
    def __init__(self, key: str, *, lifetime: timedelta = timedelta(hours=8)) -> None:
        self._key = key
        self._lifetime = lifetime

    def issue(self, user_id: UUID) -> tuple[str, datetime]:
        now = datetime.now(UTC)
        expires_at = now + self._lifetime
        claims = {
            "iss": "core",
            "sub": str(user_id),
            "iat": now,
            "exp": expires_at,
            "jti": str(uuid4()),
        }
        token = jwt.encode(
            claims,
            self._key,
            algorithm="HS256",
        )
        return token, expires_at

    def verify(self, token: str) -> UUID:
        try:
            claims = jwt.decode(
                token,
                self._key,
                algorithms=["HS256"],
                issuer="core",
                options={"require": ["exp"]},
            )
            return UUID(str(claims["sub"]))
        except (InvalidTokenError, KeyError, ValueError) as error:
            raise InvalidSessionTokenError("invalid session token") from error
