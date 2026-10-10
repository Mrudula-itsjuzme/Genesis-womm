"""Authenticated proposal document routes backed by the Core proposal service."""

import asyncio
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile, status

from app.api.deps import get_proposal_service, require_session_actor
from app.api.errors import error_responses
from app.domain.authz import Actor
from app.domain.enums import ErrorCode
from app.schemas.proposals import (
    ProposalDownloadUrlOut,
    ProposalOut,
    ProposalStatusPatch,
    ProposalUploadOut,
)
from app.services.ports import ProposalRecord
from app.services.proposals import ProposalService, ReviewAction
from app.services.schedule_write import RequestContext

router = APIRouter(
    prefix="/api/v1", tags=["proposals"], dependencies=[Depends(require_session_actor)]
)
SessionActor = Annotated[Actor, Depends(require_session_actor)]


def _out(record: ProposalRecord) -> ProposalOut:
    return ProposalOut.model_validate(record, from_attributes=True)


@router.post(
    "/clubs/{club_id}/events/{event_id}/proposals",
    status_code=status.HTTP_201_CREATED,
    response_model=ProposalUploadOut,
    responses=error_responses(
        ErrorCode.UNAUTHENTICATED,
        ErrorCode.FORBIDDEN,
        ErrorCode.NOT_FOUND,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.DEPENDENCY_UNAVAILABLE,
    ),
)
async def upload_proposal(
    club_id: UUID,
    event_id: UUID,
    file: Annotated[UploadFile, File(description="Event proposal PDF document")],
    actor: SessionActor,
    service: Annotated[ProposalService, Depends(get_proposal_service)],
    request: Request,
    title: Annotated[str, Form(description="Title of the proposal")] = "Event Proposal",
) -> ProposalUploadOut:
    content = await file.read()
    record = await asyncio.to_thread(
        service.submit,
        RequestContext(actor=actor, request_id=str(request.state.request_id)),
        club_id=club_id,
        event_id=event_id,
        title=title,
        content=content,
    )
    return ProposalUploadOut.model_validate(record, from_attributes=True)


@router.get(
    "/proposals/{proposal_id}",
    response_model=ProposalOut,
    responses=error_responses(
        ErrorCode.UNAUTHENTICATED,
        ErrorCode.FORBIDDEN,
        ErrorCode.NOT_FOUND,
        ErrorCode.VALIDATION_ERROR,
    ),
)
def get_proposal(
    proposal_id: UUID,
    actor: SessionActor,
    service: Annotated[ProposalService, Depends(get_proposal_service)],
) -> ProposalOut:
    return _out(service.get(actor, proposal_id))


@router.get(
    "/proposals/{proposal_id}/download-url",
    response_model=ProposalDownloadUrlOut,
    responses=error_responses(
        ErrorCode.UNAUTHENTICATED,
        ErrorCode.FORBIDDEN,
        ErrorCode.NOT_FOUND,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.DEPENDENCY_UNAVAILABLE,
    ),
)
def download_url(
    proposal_id: UUID,
    actor: SessionActor,
    service: Annotated[ProposalService, Depends(get_proposal_service)],
    request: Request,
) -> ProposalDownloadUrlOut:
    link = service.download_url(
        RequestContext(actor=actor, request_id=str(request.state.request_id)), proposal_id
    )
    return ProposalDownloadUrlOut(download_url=link.url, expires_in_seconds=link.expires_in_seconds)


@router.patch(
    "/proposals/{proposal_id}/status",
    response_model=ProposalOut,
    responses=error_responses(
        ErrorCode.UNAUTHENTICATED,
        ErrorCode.FORBIDDEN,
        ErrorCode.NOT_FOUND,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.INVALID_TRANSITION,
    ),
)
def review_proposal(
    proposal_id: UUID,
    payload: ProposalStatusPatch,
    actor: SessionActor,
    service: Annotated[ProposalService, Depends(get_proposal_service)],
    request: Request,
) -> ProposalOut:
    record = service.review(
        RequestContext(actor=actor, request_id=str(request.state.request_id)),
        proposal_id,
        ReviewAction(payload.action),
        payload.review_note,
    )
    return _out(record)
