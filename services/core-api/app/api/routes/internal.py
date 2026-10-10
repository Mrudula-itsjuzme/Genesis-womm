"""The narrow facade the Agent uses (spine AD-10).

Every call is authorized as the delegated user, never as a service. Responses are
field-allowlisted DTOs; no route here can reach student-private data, contacts or finances.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header

from app.api.deps import delegation_bearer, internal_key
from app.api.errors import STUB_OPENAPI, not_implemented, stub_errors
from app.domain.enums import ErrorCode
from app.schemas.agent import AgentAction, AgentActionCreate, AgentConflictCheckRequest
from app.schemas.events import ConflictCheckOut, EventOut

router = APIRouter(
    prefix="/internal/v1",
    tags=["internal: agent facade"],
    dependencies=[Depends(delegation_bearer), Depends(internal_key)],
)

IdempotencyKey = Annotated[
    str | None,
    Header(alias="Idempotency-Key", max_length=128, description="Makes a retried POST safe."),
]


@router.post(
    "/agent-tools/check_event_conflicts",
    response_model=ConflictCheckOut,
    summary="Run the conflict engine for a saved event or an unsaved candidate",
    responses=stub_errors(ErrorCode.NOT_FOUND),
    openapi_extra=STUB_OPENAPI,
)
def check_event_conflicts(payload: AgentConflictCheckRequest) -> ConflictCheckOut:
    not_implemented("Agent conflict check")


@router.get(
    "/agent-tools/events/{event_id}",
    response_model=EventOut,
    summary="Read one event as the delegated user",
    responses=stub_errors(ErrorCode.NOT_FOUND),
    openapi_extra=STUB_OPENAPI,
)
def get_event_details(event_id: UUID) -> EventOut:
    not_implemented("Agent event lookup")


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
    payload: AgentActionCreate, idempotency_key: IdempotencyKey = None
) -> AgentAction:
    not_implemented("Agent action filing")
