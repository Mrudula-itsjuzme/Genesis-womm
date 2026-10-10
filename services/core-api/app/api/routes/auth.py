"""Authentication endpoints for the seeded hackathon demo directory."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_session_service
from app.api.errors import ApiError, error_responses
from app.domain.enums import ErrorCode
from app.schemas.auth import DemoLoginRequest, MembershipOut, SessionOut, UserOut
from app.services.sessions import IssuedSession, SessionService

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


def _to_session_out(issued: IssuedSession) -> SessionOut:
    return SessionOut(
        access_token=issued.access_token,
        expires_at=issued.expires_at,
        user=UserOut(
            id=issued.user.id,
            email=issued.user.email,
            display_name=issued.user.display_name,
            campus_admin=issued.user.campus_admin,
            memberships=[
                MembershipOut(
                    club_id=membership.club_id,
                    club_name=membership.club_name,
                    role=membership.role,
                )
                for membership in issued.user.memberships
            ],
            synthetic=issued.user.is_synthetic,
        ),
    )


@router.post(
    "/demo-login",
    response_model=SessionOut,
    summary="Create a session for a seeded demo user",
    description=(
        "Demo-only seeded-directory login. Production SSO replaces this endpoint's identity "
        "verification without changing authorization rules."
    ),
    responses=error_responses(ErrorCode.UNAUTHENTICATED, ErrorCode.VALIDATION_ERROR),
)
def demo_login(
    payload: DemoLoginRequest,
    sessions: Annotated[SessionService, Depends(get_session_service)],
) -> SessionOut:
    issued = sessions.issue_for_demo_email(payload.email)
    if issued is None:
        raise ApiError(ErrorCode.UNAUTHENTICATED, "Invalid demo credentials.")
    return _to_session_out(issued)
