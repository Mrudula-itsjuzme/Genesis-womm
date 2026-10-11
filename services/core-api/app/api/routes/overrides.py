from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_schedule_write_service, require_session_actor
from app.api.errors import route_errors
from app.domain.authz import Actor
from app.domain.enums import ErrorCode
from app.schemas.events import OverrideOut, OverrideRequest
from app.services.schedule_write import EvidenceInput, RequestContext, ScheduleWriteService

router = APIRouter(
    prefix="/api/v1/overrides",
    tags=["overrides"],
)


@router.post(
    "",
    response_model=OverrideOut,
    summary="Create a new schedule conflict override",
    description="Waive one constraint for one pair of events. Campus admins only.",
    responses=route_errors(ErrorCode.DUPLICATE_OVERRIDE),
)
def create_override(
    payload: OverrideRequest,
    actor: Annotated[Actor, Depends(require_session_actor)],
    service: Annotated[ScheduleWriteService, Depends(get_schedule_write_service)],
    request: Request,
) -> OverrideOut:
    ctx = RequestContext(
        actor=actor,
        request_id=str(request.state.request_id),
        idempotency_key=None,
    )
    evidence_input = None
    if payload.evidence:
        evidence_input = EvidenceInput(
            kind=payload.evidence.kind,
            reference=payload.evidence.reference,
            captured_at=payload.evidence.captured_at,
            issuer=payload.evidence.issuer,
        )

    result = service.create_override(
        ctx,
        scope=payload.scope,
        event_a_id=payload.event_a_id,
        event_b_id=payload.event_b_id,
        reason=payload.reason,
        evidence=evidence_input,
    )

    return OverrideOut(
        id=result.override.id,
        scope=result.override.scope,
        event_a_id=result.override.event_a_id,
        event_b_id=result.override.event_b_id,
        reason=result.override.reason,
        authorizer_id=result.override.authorized_by,
        evidence_id=result.override.evidence_id,
        created_at=result.override.created_at,
    )
