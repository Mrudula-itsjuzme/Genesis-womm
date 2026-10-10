"""Request dependencies and the declared security schemes.

The schemes document the contract for callers today. They are not enforced yet: Core's
delegation token is forwarded to Core, which verifies it (spine AD-10), and the internal key
check lands with the orchestration slice.
"""

from typing import cast

from fastapi import Request
from fastapi.security import APIKeyHeader, HTTPBearer

from app.orchestration.readiness import ReadinessService

delegation_bearer = HTTPBearer(
    auto_error=False,
    scheme_name="delegationBearer",
    description=(
        "Short-lived delegation JWT minted by Core for this turn. The Agent forwards it to "
        "Core unmodified and never decodes it."
    ),
)
internal_key = APIKeyHeader(
    name="X-Internal-Key",
    auto_error=False,
    scheme_name="internalKey",
    description="Shared service-to-service key. Required outside APP_ENV=local.",
)


def get_readiness(request: Request) -> ReadinessService:
    return cast(ReadinessService, request.app.state.readiness)
