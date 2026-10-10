"""Agent orchestration routes.

All three endpoints are now implemented. They delegate to OrchestrationEngine
via workflow functions. The engine enforces the tool allowlist, max-call count,
per-tool timeouts, and trace collection on every turn.

Security model (spine AD-10):
- delegation_bearer: Core's delegation JWT is forwarded to Core unmodified.
- internal_key: verified at the dependency level outside APP_ENV=local.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials

from app.api.deps import delegation_bearer, internal_key
from app.api.errors import ApiError, stub_errors
from app.orchestration.engine import OrchestrationEngine
from app.orchestration.workflows import run_analyze_change, run_chat, run_plan_event
from app.ports.core import CallContext
from app.ports.errors import (
    ContractViolationError,
    DependencyUnavailableError,
)
from app.schemas.chat import AgentTurnRequest, AnalyzeChangeRequest, ChatResponse, PlanEventRequest
from app.schemas.enums import ErrorCode

router = APIRouter(
    prefix="/v1/agent",
    tags=["agent"],
    dependencies=[Depends(delegation_bearer), Depends(internal_key)],
)

_ERRORS = stub_errors(ErrorCode.DEPENDENCY_UNAVAILABLE, ErrorCode.AGENT_OUTPUT_INVALID)

_OPENAPI_IMPLEMENTED = {"x-implementation-status": "implemented"}


def _engine(request: Request) -> OrchestrationEngine:
    engine: OrchestrationEngine | None = getattr(request.app.state, "engine", None)
    if engine is None:
        raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE, "Orchestration engine not initialised.")
    return engine


def _call_context(request: Request) -> CallContext:
    # Extract bearer token forwarded by Core; fall back to empty string in local/test env.
    credentials = request.scope.get("_delegation_bearer")
    token: str = credentials.credentials if credentials else ""
    return CallContext(
        request_id=request.state.request_id,
        delegation_token=token,
    )


def _map_port_error(exc: Exception) -> ApiError:
    if isinstance(exc, DependencyUnavailableError):
        return ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE, str(exc))
    if isinstance(exc, ContractViolationError):
        return ApiError(ErrorCode.AGENT_OUTPUT_INVALID, str(exc))
    return ApiError(ErrorCode.INTERNAL_ERROR, "An internal error occurred.")


@router.post(
    "/chat",
    response_model=ChatResponse,
    summary="Run one conversational turn",
    description=(
        "Called by Core with a delegation token. Stateless: the caller supplies bounded history. "
        "Replies describe proposals as proposed, never as done."
    ),
    responses=_ERRORS,
    openapi_extra=_OPENAPI_IMPLEMENTED,
)
async def chat(
    payload: AgentTurnRequest,
    request: Request,
    bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(delegation_bearer)] = None,
) -> ChatResponse:
    request.scope["_delegation_bearer"] = bearer
    engine = _engine(request)
    ctx = _call_context(request)
    try:
        return await run_chat(payload, engine, ctx)
    except (DependencyUnavailableError, ContractViolationError) as exc:
        raise _map_port_error(exc) from exc


@router.post(
    "/plan-event",
    response_model=ChatResponse,
    summary="Turn a natural-language plan into a proposal",
    description="Asks for missing date, time or venue instead of guessing.",
    responses=_ERRORS,
    openapi_extra=_OPENAPI_IMPLEMENTED,
)
async def plan_event(
    payload: PlanEventRequest,
    request: Request,
    bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(delegation_bearer)] = None,
) -> ChatResponse:
    request.scope["_delegation_bearer"] = bearer
    engine = _engine(request)
    ctx = _call_context(request)
    try:
        return await run_plan_event(payload, engine, ctx)
    except (DependencyUnavailableError, ContractViolationError) as exc:
        raise _map_port_error(exc) from exc


@router.post(
    "/analyze-change",
    response_model=ChatResponse,
    summary="Explain the deterministic impact of a change",
    description="Explains Core's impact report and drafts follow-ups; it never decides impact.",
    responses=_ERRORS,
    openapi_extra=_OPENAPI_IMPLEMENTED,
)
async def analyze_change(
    payload: AnalyzeChangeRequest,
    request: Request,
    bearer: Annotated[HTTPAuthorizationCredentials | None, Depends(delegation_bearer)] = None,
) -> ChatResponse:
    request.scope["_delegation_bearer"] = bearer
    engine = _engine(request)
    ctx = _call_context(request)
    try:
        return await run_analyze_change(payload, engine, ctx)
    except (DependencyUnavailableError, ContractViolationError) as exc:
        raise _map_port_error(exc) from exc
