from fastapi import APIRouter, Depends

from app.api.deps import delegation_bearer, internal_key
from app.api.errors import STUB_OPENAPI, not_implemented, stub_errors
from app.schemas.chat import AgentTurnRequest, AnalyzeChangeRequest, ChatResponse, PlanEventRequest
from app.schemas.enums import ErrorCode

router = APIRouter(
    prefix="/v1/agent",
    tags=["agent"],
    dependencies=[Depends(delegation_bearer), Depends(internal_key)],
)

_ERRORS = stub_errors(ErrorCode.DEPENDENCY_UNAVAILABLE, ErrorCode.AGENT_OUTPUT_INVALID)


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Run one conversational turn",
    description=(
        "Called by Core with a delegation token. Stateless: the caller supplies bounded history. "
        "Replies describe proposals as proposed, never as done."
    ),
    responses=_ERRORS,
    openapi_extra=STUB_OPENAPI,
)
async def chat(payload: AgentTurnRequest) -> ChatResponse:
    not_implemented("Agent chat")


@router.post(
    "/plan-event",
    response_model=ChatResponse,
    summary="Turn a natural-language plan into a proposal",
    description="Asks for missing date, time or venue instead of guessing.",
    responses=_ERRORS,
    openapi_extra=STUB_OPENAPI,
)
async def plan_event(payload: PlanEventRequest) -> ChatResponse:
    not_implemented("Event planning")


@router.post(
    "/analyze-change",
    response_model=ChatResponse,
    summary="Explain the deterministic impact of a change",
    description="Explains Core's impact report and drafts follow-ups; it never decides impact.",
    responses=_ERRORS,
    openapi_extra=STUB_OPENAPI,
)
async def analyze_change(payload: AnalyzeChangeRequest) -> ChatResponse:
    not_implemented("Change analysis")
