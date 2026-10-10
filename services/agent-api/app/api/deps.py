"""Request dependencies and the declared security schemes.

Every turn costs model usage and acts as a user, so the Agent only accepts one from Core: the
internal key proves the caller, and a delegation token must be present to forward. The Agent never
decodes that token (Core verifies it on every call, spine AD-10); it only insists on having one.
"""

import hmac
from typing import Annotated, cast

from fastapi import Depends, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.api.errors import ApiError
from app.orchestration.readiness import ReadinessService
from app.schemas.enums import ErrorCode

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


def require_internal_key(
    provided: Annotated[str | None, Depends(internal_key)], request: Request
) -> None:
    """Prove the caller is Core. Runs before the body is read or the model is touched."""
    expected = getattr(request.app.state, "internal_api_key", None)
    if expected is None:
        raise RuntimeError("internal api key is not configured")
    if expected == "":
        return  # settings allow an empty key only when APP_ENV is local
    if provided is None or not hmac.compare_digest(provided.encode(), expected.encode()):
        raise ApiError(ErrorCode.UNAUTHENTICATED, "Valid credentials are required.")


def require_delegation_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(delegation_bearer)],
) -> str:
    """The delegation token to forward to Core, untouched. Absent is refused.

    A blank value never gets here: the HTTP stack strips header whitespace, and ``HTTPBearer``
    treats an empty credential as no credential.
    """
    if credentials is None:
        raise ApiError(ErrorCode.UNAUTHENTICATED, "Valid credentials are required.")
    return credentials.credentials
