"""The facts handed to the planning assistant with every turn (spine AD-3, AD-9).

Read from Core's own database for the signed-in person. The assistant treats them as the only
clubs and venues that exist, and Core re-checks every id it later proposes.
"""

from collections.abc import Callable

from app.domain.authz import Actor
from app.domain.enums import ResourceKind
from app.domain.time import Clock
from app.services.ports import ChatClub, ChatContext, ChatVenue, UnitOfWork

# Enough for a campus catalogue, small enough to leave the model room to think.
MAX_VENUES = 30


class ChatContextBuilder:
    def __init__(self, uow_factory: Callable[[], UnitOfWork], *, clock: Clock) -> None:
        self._uow_factory = uow_factory
        self._clock = clock

    def build(self, actor: Actor) -> ChatContext:
        with self._uow_factory() as uow:
            identity = uow.actors.load_identity(actor.user_id)
            venues, _ = uow.resources.list_resources(
                kind=ResourceKind.VENUE, query=None, limit=MAX_VENUES, offset=0
            )
        clubs = (
            ()
            if identity is None
            else tuple(ChatClub(m.club_id, m.club_name, m.role) for m in identity.memberships)
        )
        return ChatContext(
            now=self._clock.now(),
            clubs=clubs,
            venues=tuple(ChatVenue(v.id, v.name, v.capacity, v.availability_state) for v in venues),
        )
