from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request

from app.api.deps import get_agent_action_service, require_session_actor
from app.api.errors import STUB_OPENAPI, error_responses, not_implemented, stub_errors
from app.api.presenters import agent_action_out
from app.domain.authz import Actor
from app.domain.enums import AgentActionStatus, ErrorCode
from app.schemas.agent import (
    AgentAction,
    AgentActionConfirmOut,
    AgentActionList,
    ChatRequest,
    ChatResponse,
)
from app.services.agent_actions import AgentActionService
from app.services.schedule_write import RequestContext

router = APIRouter(prefix="/api/v1", tags=["agent"], dependencies=[Depends(require_session_actor)])

SessionActor = Annotated[Actor, Depends(require_session_actor)]
IdempotencyKey = Annotated[
    str | None,
    Header(alias="Idempotency-Key", max_length=128, description="Makes a retried POST safe."),
]


@router.post(
    "/agent/chat",
    response_model=ChatResponse,
    summary="Ask the planning assistant",
    description=(
        "Core mints a short-lived delegation token for the caller and relays one turn to the "
        "Agent. The reply describes proposals as proposed, never as done."
    ),
    responses=stub_errors(ErrorCode.DEPENDENCY_UNAVAILABLE, ErrorCode.AGENT_OUTPUT_INVALID),
    openapi_extra=STUB_OPENAPI,
)
def chat(payload: ChatRequest) -> ChatResponse:
    not_implemented("Agent chat")


@router.get(
    "/agent-actions",
    response_model=AgentActionList,
    summary="List the caller's agent proposals",
    description="Only proposals filed for the signed-in person, newest first.",
    responses=error_responses(
        ErrorCode.UNAUTHENTICATED, ErrorCode.FORBIDDEN, ErrorCode.VALIDATION_ERROR
    ),
)
def list_agent_actions(
    actor: SessionActor,
    service: Annotated[AgentActionService, Depends(get_agent_action_service)],
    status: AgentActionStatus | None = None,
    event_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AgentActionList:
    records, total = service.list_for(
        actor, status=status, event_id=event_id, limit=limit, offset=offset
    )
    return AgentActionList(
        items=[agent_action_out(record) for record in records],
        limit=limit,
        offset=offset,
        total=total,
    )


@router.post(
    "/agent-actions/{action_id}/confirm",
    response_model=AgentActionConfirmOut,
    summary="Execute an agent proposal as the signed-in human",
    description=(
        "The only way a proposal takes effect, and only for the person it was filed for. Core "
        "does the work as that person through the normal write path, so their current role is "
        "re-checked. Confirming is idempotent per proposal: a repeat returns the same result "
        "and never creates a second event, so the Idempotency-Key header is accepted for "
        "uniformity but not needed. Only event drafts can be confirmed today."
    ),
    responses=error_responses(
        ErrorCode.UNAUTHENTICATED,
        ErrorCode.FORBIDDEN,
        ErrorCode.NOT_FOUND,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.INVALID_TRANSITION,
    ),
)
def confirm_agent_action(
    action_id: UUID,
    actor: SessionActor,
    service: Annotated[AgentActionService, Depends(get_agent_action_service)],
    request: Request,
    idempotency_key: IdempotencyKey = None,
) -> AgentActionConfirmOut:
    done = service.confirm(
        RequestContext(actor=actor, request_id=str(request.state.request_id)), action_id
    )
    return AgentActionConfirmOut(
        action=agent_action_out(done.action),
        created_entity_type=done.created_entity_type,
        created_entity_id=done.created_entity_id,
    )


@router.post(
    "/agent-actions/{action_id}/reject",
    response_model=AgentAction,
    summary="Dismiss an agent proposal",
    description="Only the person it was filed for. Rejecting twice returns the same answer.",
    responses=error_responses(
        ErrorCode.UNAUTHENTICATED,
        ErrorCode.FORBIDDEN,
        ErrorCode.NOT_FOUND,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.INVALID_TRANSITION,
    ),
)
def reject_agent_action(
    action_id: UUID,
    actor: SessionActor,
    service: Annotated[AgentActionService, Depends(get_agent_action_service)],
    request: Request,
) -> AgentAction:
    rejected = service.reject(
        RequestContext(actor=actor, request_id=str(request.state.request_id)), action_id
    )
    return agent_action_out(rejected)
