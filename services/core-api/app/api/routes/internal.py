"""The narrow facade the Agent uses (spine AD-10).

Every call is authorized as the delegated user, never as a service. Responses are
field-allowlisted DTOs; no route here can reach student-private data, contacts or finances.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header

from app.api.deps import (
    get_conflict_check_service,
    get_event_read_service,
    require_delegated_actor,
    require_internal_key,
)
from app.api.errors import STUB_OPENAPI, error_responses, not_implemented, stub_errors
from app.api.presenters import conflict_check_out, event_out
from app.domain.authz import Actor
from app.domain.enums import ErrorCode
from app.schemas.agent import AgentAction, AgentActionCreate, AgentConflictCheckRequest
from app.schemas.events import ConflictCheckOut, EventOut
from app.services.conflict_checks import ConflictCheckService
from app.services.event_reads import EventReadService

router = APIRouter(
    prefix="/internal/v1",
    tags=["internal: agent facade"],
    dependencies=[Depends(require_internal_key)],
)

IdempotencyKey = Annotated[
    str | None,
    Header(alias="Idempotency-Key", max_length=128, description="Makes a retried POST safe."),
]
DelegatedActor = Annotated[Actor, Depends(require_delegated_actor)]


@router.post(
    "/agent-tools/check_event_conflicts",
    response_model=ConflictCheckOut,
    summary="Run the conflict engine for a saved event or an unsaved candidate",
    description=(
        "Name either `event_id` (a saved event) or `club_id` with `start_at` and `end_at` (a "
        "candidate). For a candidate `event_id` is null in the result and the nil UUID stands for "
        "it in each conflict's `event_ids`. Advisory: writes re-check inside the transaction."
    ),
    responses=error_responses(
        ErrorCode.UNAUTHENTICATED,
        ErrorCode.FORBIDDEN,
        ErrorCode.NOT_FOUND,
        ErrorCode.VALIDATION_ERROR,
    ),
)
def check_event_conflicts(
    payload: AgentConflictCheckRequest,
    actor: DelegatedActor,
    service: Annotated[ConflictCheckService, Depends(get_conflict_check_service)],
) -> ConflictCheckOut:
    result = service.check_request(
        actor,
        event_id=payload.event_id,
        club_id=payload.club_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        resource_id=payload.resource_id,
        resource_id_was_provided="resource_id" in payload.model_fields_set,
        as_status=payload.as_status,
    )
    return conflict_check_out(result)


@router.get(
    "/agent-tools/events/{event_id}",
    response_model=EventOut,
    summary="Read one event as the delegated user",
    responses=error_responses(
        ErrorCode.UNAUTHENTICATED,
        ErrorCode.FORBIDDEN,
        ErrorCode.NOT_FOUND,
        ErrorCode.VALIDATION_ERROR,
    ),
)
def get_event_details(
    event_id: UUID,
    actor: DelegatedActor,
    service: Annotated[EventReadService, Depends(get_event_read_service)],
) -> EventOut:
    view = service.get(actor, event_id)
    return event_out(view.event, view.availability)


@router.post(
    "/agent-actions",
    status_code=201,
    response_model=AgentAction,
    summary="File a proposal for a human to confirm",
    description=(
        "The Agent's only write. Creates a PROPOSED action; it can never confirm an event, "
        "create an override or send a message."
    ),
    responses=stub_errors(ErrorCode.NOT_FOUND, ErrorCode.IDEMPOTENCY_MISMATCH),
    openapi_extra=STUB_OPENAPI,
)
def file_agent_action(
    payload: AgentActionCreate,
    actor: DelegatedActor,
    idempotency_key: IdempotencyKey = None,
) -> AgentAction:
    not_implemented("Agent action filing")
