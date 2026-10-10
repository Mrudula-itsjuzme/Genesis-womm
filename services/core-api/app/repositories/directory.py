"""PostgreSQL adapters for who is acting and what can be booked (spine AD-21, AD-16).

Roles are read from rows and turned into an ``Actor`` per request. Nothing a client supplied
can reach this code as a role.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.authz import Actor
from app.domain.enums import AvailabilityState, Role
from app.models.directory import Club, Membership, Resource, User
from app.services.ports import MembershipIdentity, UserIdentity


class SqlClubReader:
    def __init__(self, session: Session) -> None:
        self._session = session

    def exists(self, club_id: UUID) -> bool:
        found = self._session.scalar(select(Club.id).where(Club.id == club_id))
        return found is not None


class SqlResourceReader:
    def __init__(self, session: Session) -> None:
        self._session = session

    def availability_of(self, resource_id: UUID) -> AvailabilityState | None:
        state = self._session.scalar(
            select(Resource.availability_state).where(Resource.id == resource_id)
        )
        return None if state is None else AvailabilityState(state)


class SqlActorReader:
    def __init__(self, session: Session) -> None:
        self._session = session

    def load_actor(self, user_id: UUID, *, via_agent: bool = False) -> Actor | None:
        user = self._session.execute(select(User.campus_admin).where(User.id == user_id)).first()
        if user is None:
            return None
        memberships = {
            club_id: Role(role)
            for club_id, role in self._session.execute(
                select(Membership.club_id, Membership.role).where(Membership.user_id == user_id)
            )
        }
        return Actor(
            user_id=user_id,
            campus_admin=user.campus_admin,
            memberships=memberships,
            via_agent=via_agent,
        )

    def load_identity(self, user_id: UUID) -> UserIdentity | None:
        user = self._session.scalar(select(User).where(User.id == user_id))
        if user is None:
            return None
        memberships = tuple(
            MembershipIdentity(club_id=club_id, club_name=club_name, role=Role(role))
            for club_id, club_name, role in self._session.execute(
                select(Membership.club_id, Club.name, Membership.role)
                .join(Club, Club.id == Membership.club_id)
                .where(Membership.user_id == user_id)
                .order_by(Club.name, Membership.club_id)
            )
        )
        return UserIdentity(
            id=user.id,
            email=user.email,
            display_name=user.display_name,
            campus_admin=user.campus_admin,
            memberships=memberships,
            is_synthetic=user.is_synthetic,
        )

    def load_identity_by_email(self, email: str) -> UserIdentity | None:
        user_id = self._session.scalar(select(User.id).where(User.email == email))
        return None if user_id is None else self.load_identity(user_id)
