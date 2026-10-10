from typing import Annotated

from fastapi import APIRouter, Depends

from app import __version__
from app.api.deps import get_readiness
from app.api.errors import ApiError, error_responses
from app.orchestration.readiness import ReadinessService
from app.schemas.enums import ErrorCode
from app.schemas.health import HealthOut, ReadyOut

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut, summary="Process liveness")
async def health() -> HealthOut:
    return HealthOut(status="ok", service="agent-api", version=__version__)


@router.get(
    "/ready",
    response_model=ReadyOut,
    summary="A model provider is configured",
    responses=error_responses(ErrorCode.DEPENDENCY_UNAVAILABLE),
)
async def ready(readiness: Annotated[ReadinessService, Depends(get_readiness)]) -> ReadyOut:
    report = readiness.check()
    if not report.ready:
        raise ApiError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            "Agent API is not ready.",
            details=[{"check": name, "ok": ok} for name, ok in report.checks.items()],
        )
    return ReadyOut(
        status="ready",
        checks=report.checks,
        informational={"model_provider": report.provider},
    )
