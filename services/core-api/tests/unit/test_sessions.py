from datetime import UTC, timedelta
from uuid import UUID, uuid4

from app.clients.tokens import PyJwtTokenService
from app.domain.enums import Role
from app.services.ports import MembershipIdentity, UserIdentity
from app.services.sessions import SessionService


class FakeActors:
    def __init__(self, users: dict[str, UserIdentity]) -> None:
        self._users = users
        self.queried_email: str | None = None

    def load_identity_by_email(self, email: str) -> UserIdentity | None:
        self.queried_email = email
        return self._users.get(email)


class FakeUnitOfWork:
    def __init__(self, actors: FakeActors) -> None:
        self.actors = actors

    def __enter__(self) -> "FakeUnitOfWork":
        return self

    def __exit__(self, *_: object) -> None:
        return None


def user_identity(user_id: UUID) -> UserIdentity:
    return UserIdentity(
        id=user_id,
        email="organizer@example.invalid",
        display_name="Demo Organizer",
        campus_admin=False,
        memberships=(
            MembershipIdentity(club_id=uuid4(), club_name="Robotics", role=Role.ORGANIZER),
        ),
        is_synthetic=True,
    )


def test_demo_login_normalizes_email_and_returns_signed_session() -> None:
    user = user_identity(uuid4())
    actors = FakeActors({user.email: user})
    service = SessionService(
        lambda: FakeUnitOfWork(actors),
        PyJwtTokenService("s" * 40, lifetime=timedelta(hours=1)),
    )

    session = service.issue_for_demo_email("  ORGANIZER@EXAMPLE.INVALID  ")

    assert session is not None
    assert (session.user, session.expires_at.tzinfo) == (user, UTC)
    assert actors.queried_email == user.email
    assert PyJwtTokenService("s" * 40).verify(session.access_token) == user.id


def test_demo_login_does_not_issue_a_token_for_unknown_email() -> None:
    actors = FakeActors({})
    service = SessionService(
        lambda: FakeUnitOfWork(actors),
        PyJwtTokenService("s" * 40),
    )

    assert service.issue_for_demo_email("unknown@example.invalid") is None
    assert actors.queried_email == "unknown@example.invalid"
