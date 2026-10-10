"""Authorized read projections for events."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.authz import Action, Actor, Resource, Visibility, authorize
from app.domain.enums import AvailabilityState, EventStatus
from app.domain.lifecycle import NotAuthorizedError
from app.services.errors import NotFoundError
from app.services.ports import EventRecord, UnitOfWork


@dataclass(frozen=True)
class EventView:
    event: EventRecord
    availability: AvailabilityState


class EventReadService:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def get(self, actor: Actor, event_id: UUID) -> EventView:
        with self._uow_factory() as uow:
            event = uow.events.get(event_id)
            if event is None:
                raise NotFoundError("event", event_id)
            return self._view(
                actor,
                event,
                uow.resources.availability_of(event.resource_id)
                if event.resource_id
                else AvailabilityState.UNKNOWN,
            )

    def list(
        self,
        actor: Actor,
        *,
        club_id: UUID | None,
        status: EventStatus | None,
        resource_id: UUID | None,
        starts_after: datetime | None,
        starts_before: datetime | None,
        limit: int,
        offset: int,
    ) -> tuple[list[EventView], int]:
        with self._uow_factory() as uow:
            events, _ = uow.events.list_events(
                club_id=club_id,
                status=status,
                resource_id=resource_id,
                starts_after=starts_after,
                starts_before=starts_before,
                limit=limit,
                offset=offset,
            )
            views = [
                self._view(
                    actor,
                    event,
                    uow.resources.availability_of(event.resource_id)
                    if event.resource_id
                    else AvailabilityState.UNKNOWN,
                )
                for event in events
                if self._visible(actor, event)
            ]
        return views, len(views)

    @staticmethod
    def _visible(actor: Actor, event: EventRecord) -> bool:
        if (
            event.status is EventStatus.DRAFT
            and event.club_id not in actor.memberships
            and not actor.campus_admin
        ):
            return False
        return authorize(actor, Action.VIEW_EVENT, Resource(club_id=event.club_id)).allowed

    def _view(
        self, actor: Actor, event: EventRecord, availability: AvailabilityState | None
    ) -> EventView:
        decision = authorize(actor, Action.VIEW_EVENT, Resource(club_id=event.club_id))
        if not decision.allowed or (
            event.status is EventStatus.DRAFT and decision.visibility is Visibility.SUMMARY
        ):
            raise NotAuthorizedError(decision)
        if decision.visibility is Visibility.SUMMARY:
            event = event.but(description=None, expected_attendance=None, audience_tags=())
        return EventView(event=event, availability=availability or AvailabilityState.UNKNOWN)
