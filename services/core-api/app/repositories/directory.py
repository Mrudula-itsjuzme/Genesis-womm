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
