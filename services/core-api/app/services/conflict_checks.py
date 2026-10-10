"""Advisory scheduling checks using the same deterministic engine as schedule writes."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.domain.authz import Action, Actor, Resource, authorize
from app.domain.enums import AvailabilityState, EventStatus
from app.domain.lifecycle import NotAuthorizedError
from app.domain.scheduling import Conflict, Policy, evaluate
from app.domain.time import Clock, InvalidIntervalError, ensure_interval
from app.services.errors import InvalidRequestError, NotFoundError
from app.services.ports import EventRecord, UnitOfWork


@dataclass(frozen=True)
class ConflictCheckResult:
    event: EventRecord
    conflicts: tuple[Conflict, ...]
    availability: AvailabilityState
    checked_at: datetime


class ConflictCheckService:
    def __init__(
        self,
        uow_factory: Callable[[], UnitOfWork],
        *,
        clock: Clock,
        policy: Policy,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._policy = policy

    def check(
        self,
        actor: Actor,
        event_id: UUID,
        *,
        start_at: datetime | None = None,
        end_at: datetime | None = None,
        resource_id: UUID | None = None,
        resource_id_was_provided: bool = False,
        as_status: EventStatus | None = None,
    ) -> ConflictCheckResult:
        with self._uow_factory() as uow:
            stored = uow.events.get(event_id)
            if stored is None:
                raise NotFoundError("event", event_id)
            decision = authorize(actor, Action.CHECK_CONFLICTS, Resource(club_id=stored.club_id))
            if not decision.allowed:
                raise NotAuthorizedError(decision)

            candidate = self._candidate(
                stored,
                start_at=start_at,
                end_at=end_at,
                resource_id=resource_id,
                resource_id_was_provided=resource_id_was_provided,
                as_status=as_status,
            )
            availability = self._availability(uow, candidate.resource_id)
            nearby = uow.events.list_scheduling_candidates(
                starts_before=candidate.end_at + self._policy.campus_gap,
                ends_after=candidate.start_at - self._policy.campus_gap,
            )
            overrides = [record.to_domain() for record in uow.overrides.for_event(candidate.id)]
            conflicts = evaluate(
                candidate.to_scheduled(),
                (record.to_scheduled() for record in nearby),
                overrides,
                self._policy,
                availability,
            )
        return ConflictCheckResult(
            event=candidate,
            conflicts=tuple(conflicts),
            availability=availability,
            checked_at=self._clock.now(),
        )

    @staticmethod
    def _candidate(
        stored: EventRecord,
        *,
        start_at: datetime | None,
        end_at: datetime | None,
        resource_id: UUID | None,
        resource_id_was_provided: bool,
        as_status: EventStatus | None,
    ) -> EventRecord:
        try:
            start, end = ensure_interval(start_at or stored.start_at, end_at or stored.end_at)
        except InvalidIntervalError as error:
            raise InvalidRequestError(str(error)) from error
        return stored.but(
            start_at=start,
            end_at=end,
            resource_id=resource_id if resource_id_was_provided else stored.resource_id,
            status=as_status or stored.status,
        )

    @staticmethod
    def _availability(uow: UnitOfWork, resource_id: UUID | None) -> AvailabilityState:
        if resource_id is None:
            return AvailabilityState.UNKNOWN
        availability = uow.resources.availability_of(resource_id)
        if availability is None:
            raise NotFoundError("resource", resource_id)
        return availability
