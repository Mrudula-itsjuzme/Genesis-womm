"""Authorized reads and advisory previews for explicit field changes."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from app.domain.authz import Action, Actor, Resource, authorize
from app.domain.enums import AvailabilityState, EventStatus
from app.domain.impact import Impact, impact_for
from app.domain.lifecycle import NotAuthorizedError, demote_on_schedule_change
from app.domain.scheduling import Conflict, Policy, evaluate
from app.domain.time import ensure_interval
from app.services.change_ports import ChangeRecord, ChangeUnitOfWork, ItemRecord
from app.services.codec import event_snapshot
from app.services.errors import InvalidRequestError, NotFoundError, StaleRevisionError
from app.services.ports import EventRecord

FIELDS = frozenset({"start_at", "end_at", "resource_id", "expected_attendance"})
TERMINAL = frozenset({EventStatus.COMPLETED, EventStatus.CANCELLED, EventStatus.REJECTED})


def change_candidate(
    event: EventRecord, changes: dict[str, Any]
) -> tuple[EventRecord, dict[str, Any]]:
    if event.status in TERMINAL:
        raise InvalidRequestError("A completed, cancelled or rejected event cannot be changed")
    if not changes or set(changes) - FIELDS:
        raise InvalidRequestError("Changes must name only schedule, venue or expected attendance")
    values = dict(changes)
    try:
        for field in ("start_at", "end_at"):
            if field in values and isinstance(values[field], str):
                values[field] = datetime.fromisoformat(values[field])
            if field in values and not isinstance(values[field], datetime):
                raise ValueError("Schedule values must be offset-aware timestamps")
        resource = values.get("resource_id")
        if isinstance(resource, str):
            values["resource_id"] = UUID(resource)
        elif resource is not None and not isinstance(resource, UUID):
            raise ValueError("resource_id must be a UUID or null")
        attendance = values.get("expected_attendance")
        if attendance is not None and (type(attendance) is not int or attendance < 0):
            raise ValueError("expected_attendance must be a non-negative integer or null")
        candidate = event.but(**values)
        start, end = ensure_interval(candidate.start_at, candidate.end_at)
        candidate = candidate.but(start_at=start, end_at=end)
    except (ValueError, TypeError) as error:
        raise InvalidRequestError(str(error)) from error
    before, after = event_snapshot(event), event_snapshot(candidate)
    actual = {field: after[field] for field in changes if before[field] != after[field]}
    if not actual:
        raise InvalidRequestError("The proposal must change at least one recorded field")
    if set(actual) & {"start_at", "end_at", "resource_id"}:
        candidate = candidate.but(status=demote_on_schedule_change(event.status))
    return candidate, actual


@dataclass(frozen=True)
class ChangePreview:
    event: EventRecord
    candidate: EventRecord
    changes: dict[str, Any]
    conflicts: tuple[Conflict, ...]
    impact: tuple[Impact, ...]
    availability: AvailabilityState


def preview_in(
    uow: ChangeUnitOfWork, event: EventRecord, changes: dict[str, Any], policy: Policy
) -> ChangePreview:
    candidate, actual = change_candidate(event, changes)
    availability = AvailabilityState.UNKNOWN
    if candidate.resource_id is not None:
        state = uow.resources.availability_of(candidate.resource_id)
        if state is None:
            raise NotFoundError("resource", candidate.resource_id)
        availability = state
    gap = policy.campus_gap
    others = uow.events.list_scheduling_candidates(
        starts_before=candidate.end_at + gap, ends_after=candidate.start_at - gap
    )
    conflicts = evaluate(
        candidate.to_scheduled(),
        [row.to_scheduled() for row in others],
        [row.to_domain() for row in uow.overrides.for_event(event.id)],
        policy,
        availability,
    )
    impact = impact_for(set(actual), uow.changes.dependencies(event.id))
    return ChangePreview(event, candidate, actual, tuple(conflicts), impact, availability)


class ChangeQueries:
    def __init__(self, factory: Callable[[], ChangeUnitOfWork], *, policy: Policy) -> None:
        self.factory, self.policy = factory, policy

    @staticmethod
    def event_for(uow: ChangeUnitOfWork, actor: Actor, event_id: UUID) -> EventRecord:
        event = uow.events.get(event_id)
        if event is None:
            raise NotFoundError("event", event_id)
        decision = authorize(actor, Action.REQUEST_CHANGE, Resource(club_id=event.club_id))
        if not decision.allowed:
            raise NotAuthorizedError(decision)
        return event

    def preview(
        self, actor: Actor, event_id: UUID, expected_revision: int, changes: dict[str, Any]
    ) -> ChangePreview:
        with self.factory() as uow:
            event = self.event_for(uow, actor, event_id)
            if event.revision != expected_revision:
                raise StaleRevisionError(event_id, expected_revision, event.revision)
            return preview_in(uow, event, changes, self.policy)

    def items(self, actor: Actor, event_id: UUID) -> list[ItemRecord]:
        with self.factory() as uow:
            self.event_for(uow, actor, event_id)
            return uow.changes.items(event_id)

    def list(
        self, actor: Actor, event_id: UUID, limit: int, offset: int
    ) -> tuple[list[ChangeRecord], int]:
        with self.factory() as uow:
            self.event_for(uow, actor, event_id)
            return uow.changes.list_for(event_id, limit, offset)

    def get(self, actor: Actor, proposal_id: UUID) -> ChangeRecord:
        with self.factory() as uow:
            record = uow.changes.get(proposal_id)
            if record is None:
                raise NotFoundError("change proposal", proposal_id)
            self.event_for(uow, actor, record.event_id)
            return record
