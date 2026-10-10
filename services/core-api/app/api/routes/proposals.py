import contextlib
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.api.deps import get_clock, get_minio_storage, session_bearer
from app.api.errors import stub_errors
from app.domain.enums import ErrorCode, ProposalStatus
from app.domain.time import Clock
from app.models.proposal import Proposal
from app.schemas.proposals import (
    ProposalDownloadUrlOut,
    ProposalOut,
    ProposalStatusPatch,
    ProposalUploadOut,
)
from app.services.minio_client import MinIOProposalStorage
from app.services.proposal_lifecycle import ProposalLifecycleManager

router = APIRouter(
    prefix="/api/v1",
    tags=["proposals"],
    dependencies=[Depends(session_bearer)],
)

# In-memory proposal store for active requests
_proposals_db: dict[UUID, Proposal] = {}


@router.post(
    "/clubs/{club_id}/events/{event_id}/proposals",
    status_code=status.HTTP_201_CREATED,
    response_model=ProposalUploadOut,
    summary="Upload an event proposal PDF",
    description="Uploads proposal binary to MinIO under event scope with SUBMITTED status.",
    responses=stub_errors(ErrorCode.VALIDATION_ERROR),

)
async def upload_proposal(
    club_id: UUID,
    event_id: UUID,
    file: Annotated[UploadFile, File(description="Event proposal PDF document")],
    storage: Annotated[MinIOProposalStorage, Depends(get_minio_storage)],
    title: Annotated[str, Form(description="Title of the proposal")] = "Event Proposal",
) -> ProposalUploadOut:
    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Proposal file cannot be empty",
        )
    if not contents.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a valid PDF starting with %PDF-",
        )

    proposal_id = uuid4()
    submitter_id = uuid4()
    revision = 1

    try:
        bucket, key, size, sha = storage.upload_proposal(
            club_id=club_id,
            event_id=event_id,
            proposal_id=proposal_id,
            revision=revision,
            file_bytes=contents,
            content_type="application/pdf",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Storage upload failure: {exc}",
        ) from exc

    proposal = Proposal(
        id=proposal_id,
        event_id=event_id,
        club_id=club_id,
        submitted_by=submitter_id,
        revision=revision,
        status=ProposalStatus.SUBMITTED,
        title=title,
        minio_bucket=bucket,
        minio_key=key,
        file_size_bytes=size,
        sha256_hash=sha,
    )
    _proposals_db[proposal_id] = proposal

    return ProposalUploadOut(
        id=proposal.id,
        event_id=proposal.event_id,
        club_id=proposal.club_id,
        revision=proposal.revision,
        status=proposal.status,
        title=proposal.title,
        minio_key=proposal.minio_key,
        file_size_bytes=proposal.file_size_bytes,
        submitted_at=proposal.submitted_at,
    )


@router.get(
    "/proposals/{proposal_id}/download-url",
    response_model=ProposalDownloadUrlOut,
    summary="Get presigned download URL for proposal",
    responses=stub_errors(ErrorCode.NOT_FOUND),

)
def get_proposal_download_url(
    proposal_id: UUID,
    storage: Annotated[MinIOProposalStorage, Depends(get_minio_storage)],
) -> ProposalDownloadUrlOut:
    proposal = _proposals_db.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")

    url = storage.generate_presigned_download_url(
        bucket=proposal.minio_bucket,
        object_key=proposal.minio_key,
        expires_in_seconds=900,
    )
    return ProposalDownloadUrlOut(download_url=url, expires_in_seconds=900)


@router.patch(
    "/proposals/{proposal_id}/status",
    response_model=ProposalOut,
    summary="Review proposal and trigger RAG ingestion on approval",
    responses=stub_errors(ErrorCode.NOT_FOUND, ErrorCode.INVALID_TRANSITION),

)
def patch_proposal_status(
    proposal_id: UUID,
    payload: ProposalStatusPatch,
    storage: Annotated[MinIOProposalStorage, Depends(get_minio_storage)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> ProposalOut:
    proposal = _proposals_db.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")

    mgr = ProposalLifecycleManager(minio_storage=storage, clock=clock)
    reviewer_id = uuid4()

    if payload.action == "approve":
        mgr.approve_proposal(proposal, reviewer_id=reviewer_id, review_note=payload.review_note)
        with contextlib.suppress(Exception):
            mgr.dispatch_rag_ingest(proposal)
    elif payload.action == "reject":
        mgr.reject_proposal(proposal, reviewer_id=reviewer_id, review_note=payload.review_note)
    elif payload.action == "request_revision":
        mgr.request_revision(proposal, reviewer_id=reviewer_id, review_note=payload.review_note)

    return ProposalOut(
        id=proposal.id,
        event_id=proposal.event_id,
        club_id=proposal.club_id,
        submitted_by=proposal.submitted_by,
        revision=proposal.revision,
        status=proposal.status,
        title=proposal.title,
        minio_bucket=proposal.minio_bucket,
        minio_key=proposal.minio_key,
        file_size_bytes=proposal.file_size_bytes,
        sha256_hash=proposal.sha256_hash,
        submitted_at=proposal.submitted_at,
        reviewed_by=proposal.reviewed_by,
        reviewed_at=proposal.reviewed_at,
        review_note=proposal.review_note,
        rag_ingested_at=proposal.rag_ingested_at,
        rag_deleted_at=proposal.rag_deleted_at,
    )


@router.get(
    "/proposals/{proposal_id}",
    response_model=ProposalOut,
    summary="Get proposal details",
    responses=stub_errors(ErrorCode.NOT_FOUND),

)
def get_proposal(proposal_id: UUID) -> ProposalOut:
    proposal = _proposals_db.get(proposal_id)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")

    return ProposalOut(
        id=proposal.id,
        event_id=proposal.event_id,
        club_id=proposal.club_id,
        submitted_by=proposal.submitted_by,
        revision=proposal.revision,
        status=proposal.status,
        title=proposal.title,
        minio_bucket=proposal.minio_bucket,
        minio_key=proposal.minio_key,
        file_size_bytes=proposal.file_size_bytes,
        sha256_hash=proposal.sha256_hash,
        submitted_at=proposal.submitted_at,
        reviewed_by=proposal.reviewed_by,
        reviewed_at=proposal.reviewed_at,
        review_note=proposal.review_note,
        rag_ingested_at=proposal.rag_ingested_at,
        rag_deleted_at=proposal.rag_deleted_at,
    )
