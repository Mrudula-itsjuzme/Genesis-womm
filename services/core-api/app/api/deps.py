"""Request dependencies and the declared security schemes.

The schemes declare the contract in OpenAPI and the `require_*` dependencies enforce it:
sessions for `/api/v1`, and for the Agent facade the internal key plus a delegation bearer.
"""

import hmac
from typing import Annotated, cast

from fastapi import Depends, Request
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer

from app.api.errors import ApiError
from app.domain.authz import Actor
from app.domain.enums import ErrorCode
from app.services.agent_actions import AgentActionService
from app.services.change_queries import ChangeQueries
from app.services.chat import ChatService
from app.services.conflict_checks import ConflictCheckService
from app.services.delegation import DelegationService
from app.services.event_reads import EventReadService
from app.services.proposals import ProposalService
from app.services.readiness import ReadinessService
from app.services.resource_reads import ResourceReadService
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


def get_conflict_check_service(request: Request) -> ConflictCheckService:
    service = getattr(request.app.state, "conflict_checks", None)
    if service is None:
        raise RuntimeError("conflict check service is not configured")
    return cast(ConflictCheckService, service)


def get_delegation_service(request: Request) -> DelegationService:
    service = getattr(request.app.state, "delegation", None)
    if service is None:
        raise RuntimeError("delegation service is not configured")
    return cast(DelegationService, service)


def get_agent_action_service(request: Request) -> AgentActionService:
    service = getattr(request.app.state, "agent_actions", None)
    if service is None:
        raise RuntimeError("agent action service is not configured")
    return cast(AgentActionService, service)


def get_chat_service(request: Request) -> ChatService:
    service = getattr(request.app.state, "chat", None)
    if service is None:
        raise RuntimeError("chat service is not configured")
    return cast(ChatService, service)


def get_resource_read_service(request: Request) -> ResourceReadService:
    service = getattr(request.app.state, "resource_reads", None)
    if service is None:
        raise RuntimeError("resource read service is not configured")
    return cast(ResourceReadService, service)


def get_proposal_service(request: Request) -> ProposalService:
    service = getattr(request.app.state, "proposals", None)
    if service is None:
        raise RuntimeError("proposal service is not configured")
    return cast(ProposalService, service)


def get_change_queries(request: Request) -> ChangeQueries:
    service = getattr(request.app.state, "changes", None)
    if service is None:
        raise RuntimeError("change queries are not configured")
    return cast(ChangeQueries, service)


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


def require_internal_key(
    provided: Annotated[str | None, Depends(internal_key)], request: Request
) -> None:
    """Prove the caller is the Agent service. Runs before any token is looked at."""
    expected = getattr(request.app.state, "internal_api_key", None)
    if expected is None:
        raise RuntimeError("internal api key is not configured")
    if expected == "":
        return  # settings allow an empty key only when APP_ENV is local
    if provided is None or not hmac.compare_digest(provided.encode(), expected.encode()):
        raise ApiError(ErrorCode.UNAUTHENTICATED, "Valid credentials are required.")


def require_delegated_actor(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(delegation_bearer)],
    delegation: Annotated[DelegationService, Depends(get_delegation_service)],
) -> Actor:
    """The user the Agent speaks for, loaded from the database and flagged as delegated."""
    actor = None if credentials is None else delegation.resolve(credentials.credentials)
    if actor is None:
        raise ApiError(ErrorCode.UNAUTHENTICATED, "Valid credentials are required.")
    return actor
