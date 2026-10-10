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

# Conflicts name the candidate first. An unsaved candidate has no id of its own, so it is
# the nil UUID, which no stored event can have (ids are random UUIDv4).
UNSAVED_CANDIDATE_ID = UUID(int=0)


@dataclass(frozen=True)
class ConflictCheckResult:
    event: EventRecord
    conflicts: tuple[Conflict, ...]
    availability: AvailabilityState
    checked_at: datetime
    saved: bool = True


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
            return self._evaluate(uow, candidate, saved=True)

    def check_candidate(
        self,
        actor: Actor,
        *,
        club_id: UUID,
        start_at: datetime,
        end_at: datetime,
        resource_id: UUID | None = None,
        as_status: EventStatus | None = None,
    ) -> ConflictCheckResult:
        """Check an event that has not been saved, for example one the Agent is drafting."""
        decision = authorize(actor, Action.CHECK_CONFLICTS, Resource(club_id=club_id))
        if not decision.allowed:
            raise NotAuthorizedError(decision)
        try:
            start, end = ensure_interval(start_at, end_at)
        except InvalidIntervalError as error:
            raise InvalidRequestError(str(error)) from error
        now = self._clock.now()
        candidate = EventRecord(
            id=UNSAVED_CANDIDATE_ID,
            club_id=club_id,
            title="Unsaved candidate",
            description=None,
            start_at=start,
            end_at=end,
            resource_id=resource_id,
            expected_attendance=None,
            audience_tags=(),
            status=as_status or EventStatus.DRAFT,
            revision=1,
            created_by=actor.user_id,
            verified_by=None,
            verified_at=None,
            evidence_id=None,
            is_synthetic=False,
            created_at=now,
            updated_at=now,
        )
        with self._uow_factory() as uow:
            if not uow.clubs.exists(club_id):
                raise NotFoundError("club", club_id)
            return self._evaluate(uow, candidate, saved=False)

    def _evaluate(
        self, uow: UnitOfWork, candidate: EventRecord, *, saved: bool
    ) -> ConflictCheckResult:
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
            saved=saved,
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
