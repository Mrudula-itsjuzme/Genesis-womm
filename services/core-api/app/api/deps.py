"""Request dependencies and the declared security schemes.

The three schemes document the contract for clients today. They are not enforced yet:
the authorization slice (Plan 01) adds actor resolution behind these same declarations.
"""

from datetime import UTC, datetime
from typing import cast

from fastapi import Request
from fastapi.security import APIKeyHeader, HTTPBearer

from app.domain.time import Clock
from app.services.minio_client import MinIOProposalStorage
from app.services.readiness import ReadinessService
from app.settings import Settings


class SystemClock:
    """Live clock producing aware UTC timestamps."""

    def now(self) -> datetime:
        return datetime.now(UTC)


def get_clock() -> Clock:
    return SystemClock()


def get_minio_storage(request: Request) -> MinIOProposalStorage:
    settings: Settings = request.app.state.settings
    return MinIOProposalStorage(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_access_key.get_secret_value(),
        secret_key=settings.minio_secret_key.get_secret_value(),
        proposal_bucket=settings.minio_proposal_bucket,
        archive_bucket=settings.minio_archive_bucket,
        use_ssl=settings.minio_use_ssl,
    )


def get_readiness(request: Request) -> ReadinessService:
    return cast(ReadinessService, request.app.state.readiness)


session_bearer = HTTPBearer(
    auto_error=False,
    scheme_name="sessionBearer",
    description="Core-issued session JWT for a signed-in user (demo-login outside production).",
)
delegation_bearer = HTTPBearer(
    auto_error=False,
    scheme_name="delegationBearer",
    description="Short-lived delegation JWT that Core mints for one Agent turn. Only /internal/v1.",
)
internal_key = APIKeyHeader(
    name="X-Internal-Key",
    auto_error=False,
    scheme_name="internalKey",
    description="Shared service-to-service key. Required outside APP_ENV=local.",
)

