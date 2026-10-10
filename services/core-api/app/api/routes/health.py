from typing import Annotated

from fastapi import APIRouter, Depends

from app import __version__
from app.api.deps import get_readiness
from app.api.errors import ApiError, error_responses
from app.domain.enums import ErrorCode
from app.schemas.health import HealthOut, ReadyOut
from app.services.readiness import ReadinessService

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthOut, summary="Process liveness")
def health() -> HealthOut:
    return HealthOut(status="ok", service="core-api", version=__version__)


@router.get(
    "/ready",
    response_model=ReadyOut,
    summary="Database reachable and migration head applied",
    responses=error_responses(ErrorCode.DEPENDENCY_UNAVAILABLE),
)
def ready(readiness: Annotated[ReadinessService, Depends(get_readiness)]) -> ReadyOut:
    report = readiness.check()
    if not report.ready:
        raise ApiError(
            ErrorCode.DEPENDENCY_UNAVAILABLE,
            "Core API is not ready.",
            details=[{"check": name, "ok": ok} for name, ok in report.checks.items()],
        )
    return ReadyOut(
        status="ready",
        checks=report.checks,
        migration_head=report.migration_head,
        expected_head=report.expected_head,
    )
