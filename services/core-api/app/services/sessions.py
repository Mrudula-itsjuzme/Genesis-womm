"""Demo session issuance over the authoritative directory.

The demo accepts a seeded email instead of a password. It is intentionally small: production
SSO can replace this boundary without changing authorization or event use cases.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from app.services.ports import DirectoryUnitOfWork, TokenService, UserIdentity


@dataclass(frozen=True)
class IssuedSession:
    access_token: str
    expires_at: datetime
    user: UserIdentity


class SessionService:
    def __init__(
        self, uow_factory: Callable[[], DirectoryUnitOfWork], tokens: TokenService
    ) -> None:
        self._uow_factory = uow_factory
        self._tokens = tokens

    def issue_for_demo_email(self, email: str) -> IssuedSession | None:
        """Issue a session for a seeded user, or return None without revealing more detail."""
        normalized_email = email.strip().casefold()
        with self._uow_factory() as uow:
            user = uow.actors.load_identity_by_email(normalized_email)
        if user is None:
            return None
        access_token, expires_at = self._tokens.issue(user.id)
        return IssuedSession(access_token=access_token, expires_at=expires_at, user=user)

    def resolve_access_token(self, access_token: str) -> UserIdentity | None:
        """Resolve a valid session token to its current server-side directory identity."""
        try:
            user_id = self._tokens.verify(access_token)
        except ValueError:
            return None
        with self._uow_factory() as uow:
            return uow.actors.load_identity(user_id)
