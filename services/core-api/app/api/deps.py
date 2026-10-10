"""Request dependencies and the declared security schemes.

The three schemes document the contract for clients today. They are not enforced yet:
the authorization slice (Plan 01) adds actor resolution behind these same declarations.
"""

from typing import cast

from fastapi import Request
from fastapi.security import APIKeyHeader, HTTPBearer

from app.services.readiness import ReadinessService

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


def get_readiness(request: Request) -> ReadinessService:
    return cast(ReadinessService, request.app.state.readiness)
