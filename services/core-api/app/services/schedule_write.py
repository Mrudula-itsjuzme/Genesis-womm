"""The single schedule write path (spine AD-4, AD-5, AD-6, AD-7, AD-8, AD-17).

Everything that sets or changes an event's interval, venue or status goes through ``commit``:

1. take the campus-wide lock, before reading anything;
2. load the other active events from committed state;
3. run the pure conflict engine;
4. if a blocking conflict appears the request is refused; otherwise write the event, a revision
   row and (by the caller) an audit row, all in the one transaction.

A blocking conflict can only arise when the candidate is CONFIRMED, so drafts and proposals
always save and simply return their warnings. No network call happens while the lock is held.
Only this module may import ``schedule_store``, where the event writers live.
"""

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

import structlog

from app.domain.authz import Action, Actor, Resource, authorize
from app.domain.enums import AvailabilityState, EventStatus, OverrideScope, Severity
from app.domain.lifecycle import (
    Evidence,
    EvidenceRequiredError,
    InvalidTransitionError,
    NotAuthorizedError,
    TransitionError,
    event_action_for,
    transition_event,
)
from app.domain.scheduling import Conflict, Policy, evaluate
from app.domain.time import Clock, ensure_interval
from app.services.codec import (
    conflict_from_json,
    conflict_to_json,
    event_from_json,
    event_snapshot,
    override_from_json,
    override_to_json,
    request_hash,
)
from app.services.errors import (
    ConflictDetectedError,
    DuplicateOverrideError,
    IdempotencyMismatchError,
    InvalidRequestError,
    NotFoundError,
    ServiceError,
    StaleRevisionError,
)
from app.services.ports import (
    AuditRecord,
    EventRecord,
    EvidenceData,
    IdSource,
    OverrideRecord,
    StoredResponse,
)
from app.services.schedule_store import ScheduleUnitOfWork

log = structlog.get_logger("schedule_write")

TITLE_MAX = 200


@dataclass(frozen=True)
class RequestContext:
    actor: Actor
    request_id: str
    idempotency_key: str | None = None


@dataclass(frozen=True)
class NewEvent:
    club_id: UUID
    title: str
    start_at: datetime
    end_at: datetime
    description: str | None = None
    resource_id: UUID | None = None
    expected_attendance: int | None = None
    audience_tags: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        start, end = ensure_interval(self.start_at, self.end_at)
        object.__setattr__(self, "start_at", start)
        object.__setattr__(self, "end_at", end)
        title = self.title.strip()
        if not title or len(title) > TITLE_MAX:
            raise ValueError(f"title must be 1 to {TITLE_MAX} characters")
        object.__setattr__(self, "title", title)
        if self.expected_attendance is not None and self.expected_attendance < 0:
            raise ValueError("expected_attendance cannot be negative")


@dataclass(frozen=True)
class EvidenceInput:
    kind: str
    reference: str
    captured_at: datetime
    issuer: str | None = None


@dataclass(frozen=True)
class WriteResult:
    event: EventRecord
    conflicts: tuple[Conflict, ...]
    venue_availability: AvailabilityState
    replayed: bool = False


@dataclass(frozen=True)
class OverrideResult:
    override: OverrideRecord
    replayed: bool = False


def _evidence_payload(evidence: EvidenceInput | None) -> dict[str, Any] | None:
    if evidence is None:
        return None
    return {
        "kind": evidence.kind,
        "reference": evidence.reference,
        "issuer": evidence.issuer,
        "captured_at": evidence.captured_at,
    }


def refusal_code(error: Exception) -> str:
    if isinstance(error, ConflictDetectedError):
        return "CONFLICT_DETECTED"
    if isinstance(error, StaleRevisionError):
        return "STALE_REVISION"
    if isinstance(error, NotFoundError):
        return "NOT_FOUND"
    if isinstance(error, IdempotencyMismatchError):
        return "IDEMPOTENCY_MISMATCH"
    if isinstance(error, DuplicateOverrideError):
        return "DUPLICATE_OVERRIDE"
    if isinstance(error, InvalidRequestError):
        return "INVALID_REQUEST"
    if isinstance(error, NotAuthorizedError):
        return "FORBIDDEN"
    if isinstance(error, InvalidTransitionError):
        return "INVALID_TRANSITION"
    if isinstance(error, EvidenceRequiredError):
        return "EVIDENCE_REQUIRED"
    return "REFUSED"


class ScheduleWriteService:
    def __init__(
        self,
        uow_factory: Callable[[], ScheduleUnitOfWork],
        *,
        clock: Clock,
        ids: IdSource,
        policy: Policy,
    ) -> None:
        self._uow_factory = uow_factory
        self._clock = clock
        self._ids = ids
        self._policy = policy

    # ---- public operations ------------------------------------------------------------

    def create_event(self, ctx: RequestContext, command: NewEvent) -> WriteResult:
        """Save a tentative proposal as a DRAFT. It always saves; conflicts return as warnings."""
        payload = {
            "club_id": command.club_id,
            "title": command.title,
            "description": command.description,
            "start_at": command.start_at,
            "end_at": command.end_at,
            "resource_id": command.resource_id,
            "expected_attendance": command.expected_attendance,
            "audience_tags": command.audience_tags,
        }
        return self._mutate(
            ctx,
            action="CREATE_EVENT",
            entity_type="event",
            entity_id=None,
            payload=payload,
            status_code=201,
            authorize_first=lambda: self._require(
                ctx.actor, Action.CREATE_EVENT, Resource(club_id=command.club_id)
            ),
            work=lambda uow, now: self._create(uow, ctx, command, now),
            encode=self._encode_write,
            decode=self._decode_write,
            entity_of=lambda result: result.event.id,
        )

    def transition_event(
        self,
        ctx: RequestContext,
        event_id: UUID,
        target: EventStatus,
        *,
        expected_revision: int,
        evidence: EvidenceInput | None = None,
    ) -> WriteResult:
        """Move an event along its lifecycle. Only a confirmation can be blocked by a conflict."""
        payload = {
            "event_id": event_id,
            "target": target,
            "expected_revision": expected_revision,
            "evidence": _evidence_payload(evidence),
        }
        return self._mutate(
            ctx,
            action="TRANSITION_EVENT",
            entity_type="event",
            entity_id=event_id,
            payload=payload,
            status_code=200,
            authorize_first=lambda: self._authorize_transition(ctx.actor, event_id, target),
            work=lambda uow, now: self._transition(
                uow, ctx, event_id, target, expected_revision, evidence, now
            ),
            encode=self._encode_write,
            decode=self._decode_write,
            entity_of=lambda result: result.event.id,
        )

    def create_override(
        self,
        ctx: RequestContext,
        *,
        scope: OverrideScope,
        event_a_id: UUID,
        event_b_id: UUID,
        reason: str,
        evidence: EvidenceInput | None = None,
    ) -> OverrideResult:
        """Waive one constraint for one pair of events. Campus admins only (spine AD-6)."""
        low, high = sorted((event_a_id, event_b_id), key=lambda value: value.int)
        payload = {
            "scope": scope,
            "event_a_id": low,
            "event_b_id": high,
            "reason": reason.strip(),
            "evidence": _evidence_payload(evidence),
        }
        return self._mutate(
            ctx,
            action="CREATE_OVERRIDE",
            entity_type="schedule_override",
            entity_id=None,
            payload=payload,
            status_code=201,
            authorize_first=lambda: self._require(ctx.actor, Action.CREATE_OVERRIDE, Resource()),
            work=lambda uow, now: self._override(uow, ctx, scope, low, high, reason, evidence, now),
            encode=lambda result: {"override": override_to_json(result.override)},
            decode=lambda data: OverrideResult(override_from_json(data["override"]), replayed=True),
            entity_of=lambda result: result.override.id,
        )

    # ---- the one place an event is written (spine AD-4) -------------------------------

    def commit(
        self,
        uow: ScheduleUnitOfWork,
        ctx: RequestContext,
        *,
        before: EventRecord | None,
        after: EventRecord,
        availability: AvailabilityState,
        reason: str,
        now: datetime,
    ) -> list[Conflict]:
        """Check ``after`` against everything else, then write it and its revision.

        The caller has already taken the campus lock. Raises ``ConflictDetectedError`` if a
        blocking conflict exists, in which case nothing has been written.
        """
        gap = self._policy.campus_gap
        nearby = uow.events.list_scheduling_candidates(
            starts_before=after.end_at + gap, ends_after=after.start_at - gap
        )
        others = [record.to_scheduled() for record in nearby]
        overrides = [record.to_domain() for record in uow.overrides.for_event(after.id)]
        conflicts = evaluate(after.to_scheduled(), others, overrides, self._policy, availability)
        if any(conflict.severity is Severity.BLOCKING for conflict in conflicts):
            raise ConflictDetectedError(conflicts)

        writers = uow.schedule
        if before is None:
            writers.events.insert(after)
        else:
            writers.events.update(after, expected_revision=before.revision)
        writers.revisions.add(
            revision_id=self._ids.new_id(),
            event_id=after.id,
            revision=after.revision,
            previous=None if before is None else event_snapshot(before),
            current=event_snapshot(after),
            actor_id=ctx.actor.user_id,
            reason=reason,
            created_at=now,
        )
        return conflicts

    # ---- the pipeline every mutation goes through (spine AD-8) ------------------------

    def _mutate[R](
        self,
        ctx: RequestContext,
        *,
        action: str,
        entity_type: str,
        entity_id: UUID | None,
        payload: dict[str, Any],
        status_code: int,
        authorize_first: Callable[[], None],
        work: Callable[[ScheduleUnitOfWork, datetime], R],
        encode: Callable[[R], dict[str, Any]],
        decode: Callable[[dict[str, Any]], R],
        entity_of: Callable[[R], UUID | None],
    ) -> R:
        digest = request_hash(action, payload)
        try:
            # Deny before taking the lock, so nobody unauthorized can queue on it.
            authorize_first()
            with self._uow_factory() as uow:
                uow.schedule.lock.acquire()
                key = ctx.idempotency_key
                if key is not None:
                    stored = uow.idempotency.get(ctx.actor.user_id, key)
                    if stored is not None:
                        if stored.request_hash != digest:
                            raise IdempotencyMismatchError(
                                "this Idempotency-Key was used for a different request"
                            )
                        return decode(stored.response)  # a retry: nothing new is written
                now = self._clock.now()
                result = work(uow, now)
                uow.audit.add(
                    self._audit(ctx, action, entity_type, entity_of(result), "SUCCESS", None, now)
                )
                if key is not None:
                    uow.idempotency.put(
                        ctx.actor.user_id,
                        key,
                        StoredResponse(digest, status_code, encode(result)),
                        now,
                    )
                uow.commit()
                return result
        except (ServiceError, TransitionError) as refusal:
            self._record_refusal(ctx, action, entity_type, entity_id, refusal)
            raise

    def _record_refusal(
        self,
        ctx: RequestContext,
        action: str,
        entity_type: str,
        entity_id: UUID | None,
        error: Exception,
    ) -> None:
        """Audit a refusal in its own transaction; the main one has already rolled back."""
        try:
            now = self._clock.now()
            with self._uow_factory() as uow:
                code = refusal_code(error)
                uow.audit.add(
                    self._audit(ctx, action, entity_type, entity_id, "REFUSED", code, now)
                )
                uow.commit()
        except Exception:
            # A broken audit write must never hide the real refusal from the caller, and neither
            # may a broken logger.
            with suppress(Exception):
                log.warning("refusal_audit_failed", action=action, request_id=ctx.request_id)

    def _audit(
        self,
        ctx: RequestContext,
        action: str,
        entity_type: str,
        entity_id: UUID | None,
        outcome: str,
        reason_code: str | None,
        now: datetime,
    ) -> AuditRecord:
        return AuditRecord(
            id=self._ids.new_id(),
            actor_id=ctx.actor.user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            outcome=outcome,
            reason_code=reason_code,
            request_id=ctx.request_id,
            via="AGENT" if ctx.actor.via_agent else "USER",
            created_at=now,
        )

    # ---- the work of each operation ---------------------------------------------------

    @staticmethod
    def _require(actor: Actor, action: Action, resource: Resource) -> None:
        decision = authorize(actor, action, resource)
        if not decision.allowed:
            raise NotAuthorizedError(decision)

    def _authorize_transition(self, actor: Actor, event_id: UUID, target: EventStatus) -> None:
        """Cheap early denial. The authoritative check re-runs inside the lock."""
        with self._uow_factory() as uow:
            record = uow.events.get(event_id)
        if record is None:
            raise NotFoundError("event", event_id)
        action = event_action_for(target)
        if action is None:
            raise InvalidTransitionError(record.status, target)
        self._require(actor, action, Resource(club_id=record.club_id))

    @staticmethod
    def _availability(uow: ScheduleUnitOfWork, resource_id: UUID | None) -> AvailabilityState:
        if resource_id is None:
            return AvailabilityState.UNKNOWN
        state = uow.resources.availability_of(resource_id)
        if state is None:
            raise NotFoundError("resource", resource_id)
        return state

    def _create(
        self, uow: ScheduleUnitOfWork, ctx: RequestContext, command: NewEvent, now: datetime
    ) -> WriteResult:
        if not uow.clubs.exists(command.club_id):
            raise NotFoundError("club", command.club_id)
        availability = self._availability(uow, command.resource_id)
        record = EventRecord(
            id=self._ids.new_id(),
            club_id=command.club_id,
            title=command.title,
            description=command.description,
            start_at=command.start_at,
            end_at=command.end_at,
            resource_id=command.resource_id,
            expected_attendance=command.expected_attendance,
            audience_tags=command.audience_tags,
            status=EventStatus.DRAFT,
            revision=1,
            created_by=ctx.actor.user_id,
            verified_by=None,
            verified_at=None,
            evidence_id=None,
            is_synthetic=False,
            created_at=now,
            updated_at=now,
        )
        conflicts = self.commit(
            uow,
            ctx,
            before=None,
            after=record,
            availability=availability,
            reason="created",
            now=now,
        )
        return WriteResult(
            event=record, conflicts=tuple(conflicts), venue_availability=availability
        )

    def _transition(
        self,
        uow: ScheduleUnitOfWork,
        ctx: RequestContext,
        event_id: UUID,
        target: EventStatus,
        expected_revision: int,
        evidence: EvidenceInput | None,
        now: datetime,
    ) -> WriteResult:
        before = uow.events.get(event_id)
        if before is None:
            raise NotFoundError("event", event_id)
        if before.revision != expected_revision:
            raise StaleRevisionError(event_id, expected_revision, before.revision)

        evidence_id = self._ids.new_id() if evidence is not None else None
        step = transition_event(
            before.status,
            target,
            actor=ctx.actor,
            club_id=before.club_id,
            evidence=None if evidence_id is None else Evidence(id=evidence_id),
            now=now,
        )
        changes: dict[str, Any] = {
            "status": step.status,
            "revision": before.revision + 1,
            "updated_at": now,
        }
        if step.verification is not None and evidence is not None and evidence_id is not None:
            uow.evidence.add(
                EvidenceData(
                    id=evidence_id,
                    kind=evidence.kind,
                    reference=evidence.reference,
                    issuer=evidence.issuer,
                    captured_at=evidence.captured_at,
                    recorded_by=ctx.actor.user_id,
                    created_at=now,
                )
            )
            changes.update(
                verified_by=step.verification.verified_by,
                verified_at=step.verification.verified_at,
                evidence_id=step.verification.evidence_id,
            )
        after = before.but(**changes)
        availability = self._availability(uow, after.resource_id)
        conflicts = self.commit(
            uow,
            ctx,
            before=before,
            after=after,
            availability=availability,
            reason=f"{before.status.value} -> {target.value}",
            now=now,
        )
        return WriteResult(event=after, conflicts=tuple(conflicts), venue_availability=availability)

    def _override(
        self,
        uow: ScheduleUnitOfWork,
        ctx: RequestContext,
        scope: OverrideScope,
        low: UUID,
        high: UUID,
        reason: str,
        evidence: EvidenceInput | None,
        now: datetime,
    ) -> OverrideResult:
        text = reason.strip()
        if not text:
            raise InvalidRequestError("an override needs a reason")
        if low == high:
            raise InvalidRequestError("an override names two different events")
        for event_id in (low, high):
            if uow.events.get(event_id) is None:
                raise NotFoundError("event", event_id)
        if uow.overrides.exists(scope, low, high):
            raise DuplicateOverrideError("an override for this scope and pair already exists")

        evidence_id: UUID | None = None
        if evidence is not None:
            evidence_id = self._ids.new_id()
            uow.evidence.add(
                EvidenceData(
                    id=evidence_id,
                    kind=evidence.kind,
                    reference=evidence.reference,
                    issuer=evidence.issuer,
                    captured_at=evidence.captured_at,
                    recorded_by=ctx.actor.user_id,
                    created_at=now,
                )
            )
        record = OverrideRecord(
            id=self._ids.new_id(),
            scope=scope,
            event_a_id=low,
            event_b_id=high,
            reason=text,
            authorized_by=ctx.actor.user_id,
            evidence_id=evidence_id,
            created_at=now,
        )
        uow.schedule.overrides.add(record)
        return OverrideResult(override=record)

    # ---- stored responses -------------------------------------------------------------

    @staticmethod
    def _encode_write(result: WriteResult) -> dict[str, Any]:
        return {
            "event": event_snapshot(result.event),
            "conflicts": [conflict_to_json(c) for c in result.conflicts],
            "venue_availability": result.venue_availability.value,
        }

    @staticmethod
    def _decode_write(data: dict[str, Any]) -> WriteResult:
        return WriteResult(
            event=event_from_json(data["event"]),
            conflicts=tuple(conflict_from_json(c) for c in data["conflicts"]),
            venue_availability=AvailabilityState(data["venue_availability"]),
            replayed=True,
        )
