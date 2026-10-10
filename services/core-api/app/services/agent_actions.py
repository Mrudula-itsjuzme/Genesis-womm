"""Agent proposals: the Agent files them, a human decides (spine AD-9, AD-10).

The Agent's only write is filing a PROPOSED action. Core checks that the payload is valid for the
operation it names, dry-runs it and stores what the dry run found. Nothing takes effect until the
person the proposal was filed for confirms it with their own session, and then Core performs the
operation as that person through the same write path as any other request.
"""

import json
from collections.abc import Callable, Mapping
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import structlog

from app.domain.authz import Action, Actor, Resource, authorize
from app.domain.enums import AgentActionStatus, AgentActionType
from app.domain.lifecycle import InvalidTransitionError, NotAuthorizedError, TransitionError
from app.domain.scheduling import Conflict
from app.domain.time import Clock
from app.services.codec import request_hash
from app.services.conflict_checks import ConflictCheckService
from app.services.errors import (
    IdempotencyMismatchError,
    InvalidRequestError,
    NotFoundError,
    ServiceError,
)
from app.services.ports import (
    AgentActionRecord,
    AgentActionUnitOfWork,
    AuditRecord,
    IdSource,
    StoredResponse,
)
from app.services.schedule_write import NewEvent, RequestContext, ScheduleWriteService, refusal_code

log = structlog.get_logger(__name__)

MAX_PAYLOAD_BYTES = 16_384
MAX_AUDIENCE_TAGS = 20
MAX_TAG_LENGTH = 40
_DRAFT_FIELDS = frozenset(
    {
        "club_id",
        "title",
        "description",
        "start_at",
        "end_at",
        "resource_id",
        "expected_attendance",
        "audience_tags",
    }
)
_DRAFT_REQUIRED = ("club_id", "title", "start_at", "end_at")
# What confirming can do today. The other proposal types need change proposals, commitments or
# drafts, which are not built; they can be filed and read but not confirmed.
_EXECUTABLE = frozenset({AgentActionType.CREATE_EVENT_DRAFT})


@dataclass(frozen=True)
class NewAgentAction:
    type: AgentActionType
    summary: str
    target_event_id: UUID | None = None
    expected_revision: int | None = None
    payload: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class FiledAction:
    action: AgentActionRecord
    replayed: bool = False


@dataclass(frozen=True)
class ConfirmedAction:
    action: AgentActionRecord
    created_entity_type: str
    created_entity_id: UUID


# ---- payloads --------------------------------------------------------------------------


def _uuid(value: object, name: str) -> UUID:
    if isinstance(value, UUID):
        return value
    if not isinstance(value, str):
        raise ValueError(f"{name} must be a UUID")
    return UUID(value)


def _instant(value: object, name: str) -> datetime:
    if isinstance(value, datetime):
        return value
    if not isinstance(value, str):
        raise ValueError(f"{name} must be an ISO 8601 timestamp")
    return datetime.fromisoformat(value)


def _tags(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list | tuple) or len(value) > MAX_AUDIENCE_TAGS:
        raise ValueError(f"audience_tags must be a list of at most {MAX_AUDIENCE_TAGS} tags")
    tags: list[str] = []
    for tag in value:
        if not isinstance(tag, str) or not tag.strip() or len(tag.strip()) > MAX_TAG_LENGTH:
            raise ValueError(f"each audience tag must be 1 to {MAX_TAG_LENGTH} characters")
        tags.append(tag.strip())
    return tuple(tags)


def _event_draft(payload: Mapping[str, Any]) -> NewEvent:
    """Parse and validate the payload of a CREATE_EVENT_DRAFT proposal."""
    unknown = sorted(set(payload) - _DRAFT_FIELDS)
    if unknown:
        raise InvalidRequestError(f"unknown event draft field: {', '.join(unknown)}")
    for name in _DRAFT_REQUIRED:
        if payload.get(name) is None:
            raise InvalidRequestError(f"{name} is required for an event draft")
    try:
        title, description = payload["title"], payload.get("description")
        if not isinstance(title, str):
            raise ValueError("title must be text")
        if description is not None and not isinstance(description, str):
            raise ValueError("description must be text")
        attendance = payload.get("expected_attendance")
        if attendance is not None and (
            isinstance(attendance, bool) or not isinstance(attendance, int)
        ):
            raise ValueError("expected_attendance must be a whole number")
        resource = payload.get("resource_id")
        return NewEvent(
            club_id=_uuid(payload["club_id"], "club_id"),
            title=title,
            description=description,
            start_at=_instant(payload["start_at"], "start_at"),
            end_at=_instant(payload["end_at"], "end_at"),
            resource_id=None if resource is None else _uuid(resource, "resource_id"),
            expected_attendance=attendance,
            audience_tags=_tags(payload.get("audience_tags")),
        )
    except ValueError as error:
        raise InvalidRequestError(str(error)) from error


def _canonical_draft(draft: NewEvent) -> dict[str, Any]:
    return {
        "club_id": str(draft.club_id),
        "title": draft.title,
        "description": draft.description,
        "start_at": draft.start_at.astimezone(UTC).isoformat(),
        "end_at": draft.end_at.astimezone(UTC).isoformat(),
        "resource_id": None if draft.resource_id is None else str(draft.resource_id),
        "expected_attendance": draft.expected_attendance,
        "audience_tags": list(draft.audience_tags),
    }


def _bounded_json(payload: Mapping[str, Any]) -> dict[str, Any]:
    try:
        encoded = json.dumps(payload, sort_keys=True)
    except (TypeError, ValueError) as error:
        raise InvalidRequestError("payload must be plain JSON") from error
    if len(encoded.encode()) > MAX_PAYLOAD_BYTES:
        raise InvalidRequestError(f"payload is too large (limit {MAX_PAYLOAD_BYTES} bytes)")
    return dict(payload)


def _confirm_key(action_id: UUID) -> str:
    return f"confirm-agent-action:{action_id}"


# ---- the service -----------------------------------------------------------------------


class AgentActionService:
    def __init__(
        self,
        uow_factory: Callable[[], AgentActionUnitOfWork],
        *,
        checks: ConflictCheckService,
        writes: ScheduleWriteService,
        clock: Clock,
        ids: IdSource,
    ) -> None:
        self._uow_factory = uow_factory
        self._checks = checks
        self._writes = writes
        self._clock = clock
        self._ids = ids

    # ---- filing ----

    def file(self, ctx: RequestContext, command: NewAgentAction) -> FiledAction:
        try:
            return self._file(ctx, command)
        except (ServiceError, TransitionError) as refusal:
            self._record_refusal(ctx, "FILE_AGENT_ACTION", None, refusal)
            raise

    def _file(self, ctx: RequestContext, command: NewAgentAction) -> FiledAction:
        with self._uow_factory() as uow:
            club_id, payload, draft = self._resolve(uow, command)
            decision = authorize(ctx.actor, Action.FILE_AGENT_ACTION, Resource(club_id=club_id))
            if not decision.allowed:
                raise NotAuthorizedError(decision)

            digest = request_hash(
                "FILE_AGENT_ACTION",
                {
                    "type": command.type.value,
                    "summary": command.summary,
                    "target_event_id": command.target_event_id,
                    "expected_revision": command.expected_revision,
                    "payload": payload,
                },
            )
            replay = self._replay(uow, ctx, digest)
            if replay is not None:
                return FiledAction(replay, replayed=True)

            now = self._clock.now()
            record = AgentActionRecord(
                id=self._ids.new_id(),
                type=command.type,
                status=AgentActionStatus.PROPOSED,
                summary=command.summary,
                requested_by=ctx.actor.user_id,
                club_id=club_id,
                target_event_id=command.target_event_id,
                expected_revision=command.expected_revision,
                payload=payload,
                conflicts=self._dry_run(ctx.actor, draft),
                decided_by=None,
                decided_at=None,
                result_entity_type=None,
                result_entity_id=None,
                created_at=now,
                updated_at=now,
            )
            uow.agent_actions.add(record)
            uow.audit.add(self._audit(ctx, "FILE_AGENT_ACTION", record.id, "SUCCESS", None, now))
            if ctx.idempotency_key is not None:
                uow.idempotency.put(
                    ctx.actor.user_id,
                    ctx.idempotency_key,
                    StoredResponse(digest, 201, {"action_id": str(record.id)}),
                    now,
                )
            uow.commit()
        return FiledAction(record)

    def _resolve(
        self, uow: AgentActionUnitOfWork, command: NewAgentAction
    ) -> tuple[UUID, dict[str, Any], NewEvent | None]:
        """The club a proposal concerns, its stored payload, and the parsed draft if it has one."""
        raw = _bounded_json(command.payload or {})
        if command.type is AgentActionType.CREATE_EVENT_DRAFT:
            if command.target_event_id is not None or command.expected_revision is not None:
                raise InvalidRequestError(
                    "an event draft names no target_event_id or expected_revision"
                )
            draft = _event_draft(raw)
            return draft.club_id, _canonical_draft(draft), draft
        if command.target_event_id is None:
            raise InvalidRequestError("target_event_id is required for this proposal")
        event = uow.events.get(command.target_event_id)
        if event is None:
            raise NotFoundError("event", command.target_event_id)
        if (
            command.type is AgentActionType.REQUEST_EVENT_CHANGE
            and command.expected_revision is None
        ):
            raise InvalidRequestError("expected_revision is required for a change request")
        return event.club_id, raw, None

    def _dry_run(self, actor: Actor, draft: NewEvent | None) -> tuple[Conflict, ...]:
        if draft is None:
            return ()
        result = self._checks.check_candidate(
            actor,
            club_id=draft.club_id,
            start_at=draft.start_at,
            end_at=draft.end_at,
            resource_id=draft.resource_id,
        )
        return result.conflicts

    @staticmethod
    def _replay(
        uow: AgentActionUnitOfWork, ctx: RequestContext, digest: str
    ) -> AgentActionRecord | None:
        if ctx.idempotency_key is None:
            return None
        stored = uow.idempotency.get(ctx.actor.user_id, ctx.idempotency_key)
        if stored is None:
            return None
        if stored.request_hash != digest:
            raise IdempotencyMismatchError("this Idempotency-Key was used for a different request")
        record = uow.agent_actions.get(UUID(stored.response["action_id"]))
        if record is None:
            raise RuntimeError("an idempotency record points at a proposal that does not exist")
        return record

    # ---- reading ----

    def list_for(
        self,
        actor: Actor,
        *,
        status: AgentActionStatus | None,
        event_id: UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[AgentActionRecord], int]:
        with self._uow_factory() as uow:
            return uow.agent_actions.list_for(
                actor.user_id, status=status, event_id=event_id, limit=limit, offset=offset
            )

    # ---- deciding ----

    def confirm(self, ctx: RequestContext, action_id: UUID) -> ConfirmedAction:
        try:
            return self._confirm(ctx, action_id)
        except (ServiceError, TransitionError) as refusal:
            self._record_refusal(ctx, "CONFIRM_AGENT_ACTION", action_id, refusal)
            raise

    def _confirm(self, ctx: RequestContext, action_id: UUID) -> ConfirmedAction:
        record = self._owned(ctx.actor, action_id)
        if record.status is AgentActionStatus.EXECUTED:
            return self._executed(record)
        if record.status is not AgentActionStatus.PROPOSED:
            raise InvalidTransitionError(record.status, AgentActionStatus.EXECUTED)
        if record.type not in _EXECUTABLE:
            raise InvalidRequestError(
                f"{record.type.value} proposals cannot be confirmed: not available yet"
            )

        # The operation runs first, under a key derived from the proposal, so a retry after a
        # crash replays the same event instead of creating a second one.
        created = self._writes.create_event(
            RequestContext(
                actor=ctx.actor,
                request_id=ctx.request_id,
                idempotency_key=_confirm_key(record.id),
            ),
            _event_draft(record.payload),
        )
        now = self._clock.now()
        with self._uow_factory() as uow:
            won = uow.agent_actions.decide(
                record.id,
                status=AgentActionStatus.EXECUTED,
                decided_by=ctx.actor.user_id,
                decided_at=now,
                result_entity_type="event",
                result_entity_id=created.event.id,
            )
            current = uow.agent_actions.get(record.id)
            if won:
                uow.audit.add(
                    self._audit(ctx, "CONFIRM_AGENT_ACTION", record.id, "SUCCESS", None, now)
                )
                uow.commit()
        if current is None:
            raise NotFoundError("agent action", record.id)
        if current.status is not AgentActionStatus.EXECUTED:
            # Someone else decided it between our check and our decision.
            raise InvalidTransitionError(current.status, AgentActionStatus.EXECUTED)
        return self._executed(current)

    def reject(self, ctx: RequestContext, action_id: UUID) -> AgentActionRecord:
        try:
            return self._reject(ctx, action_id)
        except (ServiceError, TransitionError) as refusal:
            self._record_refusal(ctx, "REJECT_AGENT_ACTION", action_id, refusal)
            raise

    def _reject(self, ctx: RequestContext, action_id: UUID) -> AgentActionRecord:
        record = self._owned(ctx.actor, action_id)
        if record.status is AgentActionStatus.REJECTED:
            return record
        if record.status is not AgentActionStatus.PROPOSED:
            raise InvalidTransitionError(record.status, AgentActionStatus.REJECTED)
        now = self._clock.now()
        with self._uow_factory() as uow:
            won = uow.agent_actions.decide(
                record.id,
                status=AgentActionStatus.REJECTED,
                decided_by=ctx.actor.user_id,
                decided_at=now,
                result_entity_type=None,
                result_entity_id=None,
            )
            current = uow.agent_actions.get(record.id)
            if won:
                uow.audit.add(
                    self._audit(ctx, "REJECT_AGENT_ACTION", record.id, "SUCCESS", None, now)
                )
                uow.commit()
        if current is None:
            raise NotFoundError("agent action", record.id)
        if current.status is not AgentActionStatus.REJECTED:
            raise InvalidTransitionError(current.status, AgentActionStatus.REJECTED)
        return current

    # ---- shared ----

    def _owned(self, actor: Actor, action_id: UUID) -> AgentActionRecord:
        """The proposal, if the actor is the person it was filed for."""
        with self._uow_factory() as uow:
            record = uow.agent_actions.get(action_id)
        if record is None:
            raise NotFoundError("agent action", action_id)
        decision = authorize(
            actor, Action.CONFIRM_AGENT_ACTION, Resource(owner_id=record.requested_by)
        )
        if not decision.allowed:
            raise NotAuthorizedError(decision)
        return record

    @staticmethod
    def _executed(record: AgentActionRecord) -> ConfirmedAction:
        if record.result_entity_type is None or record.result_entity_id is None:
            raise RuntimeError("an executed proposal must record what it created")
        return ConfirmedAction(record, record.result_entity_type, record.result_entity_id)

    def _audit(
        self,
        ctx: RequestContext,
        action: str,
        entity_id: UUID | None,
        outcome: str,
        reason_code: str | None,
        now: datetime,
    ) -> AuditRecord:
        return AuditRecord(
            id=self._ids.new_id(),
            actor_id=ctx.actor.user_id,
            action=action,
            entity_type="agent_action",
            entity_id=entity_id,
            outcome=outcome,
            reason_code=reason_code,
            request_id=ctx.request_id,
            via="AGENT" if ctx.actor.via_agent else "USER",
            created_at=now,
        )

    def _record_refusal(
        self,
        ctx: RequestContext,
        action: str,
        entity_id: UUID | None,
        error: Exception,
    ) -> None:
        """Audit a refusal in its own transaction; it must never hide the refusal itself."""
        try:
            now = self._clock.now()
            with self._uow_factory() as uow:
                uow.audit.add(
                    self._audit(ctx, action, entity_id, "REFUSED", refusal_code(error), now)
                )
                uow.commit()
        except Exception:
            with suppress(Exception):
                log.warning("refusal_audit_failed", action=action, request_id=ctx.request_id)
