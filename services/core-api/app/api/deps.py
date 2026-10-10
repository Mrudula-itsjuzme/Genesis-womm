"""Request dependencies and the declared security schemes.

The three schemes document the contract for clients today. They are not enforced yet:
the authorization slice (Plan 01) adds actor resolution behind these same declarations.
"""

from typing import Annotated, cast

from fastapi import Depends, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.api.errors import ApiError
from app.domain.authz import Actor
from app.domain.enums import ErrorCode
from app.services.event_reads import EventReadService
from app.services.readiness import ReadinessService
from app.services.schedule_write import ScheduleWriteService
from app.services.sessions import SessionService

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


def get_session_service(request: Request) -> SessionService:
    sessions = getattr(request.app.state, "sessions", None)
    if sessions is None:
        raise RuntimeError("session service is not configured")
    return cast(SessionService, sessions)


def get_schedule_write_service(request: Request) -> ScheduleWriteService:
    service = getattr(request.app.state, "schedule_write", None)
    if service is None:
        raise RuntimeError("schedule write service is not configured")
    return cast(ScheduleWriteService, service)


def get_event_read_service(request: Request) -> EventReadService:
    service = getattr(request.app.state, "event_reads", None)
    if service is None:
        raise RuntimeError("event read service is not configured")
    return cast(EventReadService, service)


def require_session_actor(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(session_bearer)],
    sessions: Annotated[SessionService, Depends(get_session_service)],
) -> Actor:
    if credentials is None:
        raise ApiError(ErrorCode.UNAUTHENTICATED, "A valid session token is required.")
    user = sessions.resolve_access_token(credentials.credentials)
    if user is None:
        raise ApiError(ErrorCode.UNAUTHENTICATED, "A valid session token is required.")
    return Actor(
        user_id=user.id,
        campus_admin=user.campus_admin,
        memberships={membership.club_id: membership.role for membership in user.memberships},
    )
