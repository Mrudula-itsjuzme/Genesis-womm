from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query

from app.api.deps import session_bearer
from app.api.errors import STUB_OPENAPI, not_implemented, stub_errors
from app.domain.enums import AgentActionStatus, ErrorCode
from app.schemas.agent import (
    AgentAction,
    AgentActionConfirmOut,
    AgentActionList,
    ChatRequest,
    ChatResponse,
)

router = APIRouter(prefix="/api/v1", tags=["agent"], dependencies=[Depends(session_bearer)])

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
    responses=stub_errors(),
    openapi_extra=STUB_OPENAPI,
)
def list_agent_actions(
    status: AgentActionStatus | None = None,
    event_id: UUID | None = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AgentActionList:
    not_implemented("Agent action listing")


@router.post(
    "/agent-actions/{action_id}/confirm",
    response_model=AgentActionConfirmOut,
    summary="Execute an agent proposal as the signed-in human",
    description=(
        "The only way a proposal takes effect. Core re-validates conflicts and the event "
        "revision inside the transaction, so a stale proposal returns 409."
    ),
    responses=stub_errors(
        ErrorCode.NOT_FOUND,
        ErrorCode.CONFLICT_DETECTED,
        ErrorCode.STALE_REVISION,
        ErrorCode.INVALID_TRANSITION,
        ErrorCode.IDEMPOTENCY_MISMATCH,
    ),
    openapi_extra=STUB_OPENAPI,
)
def confirm_agent_action(
    action_id: UUID, idempotency_key: IdempotencyKey = None
) -> AgentActionConfirmOut:
    not_implemented("Agent action confirmation")


@router.post(
    "/agent-actions/{action_id}/reject",
    response_model=AgentAction,
    summary="Dismiss an agent proposal",
    responses=stub_errors(ErrorCode.NOT_FOUND, ErrorCode.INVALID_TRANSITION),
    openapi_extra=STUB_OPENAPI,
)
def reject_agent_action(action_id: UUID) -> AgentAction:
    not_implemented("Agent action rejection")
