from datetime import datetime, timedelta
from typing import Any
from uuid import UUID

import httpx

from app.domain.enums import ProposalStatus
from app.domain.time import Clock
from app.models.proposal import Proposal
from app.services.minio_client import MinIOProposalStorage


class ProposalLifecycleManager:
    """Coordinates proposal state transitions, RAG API synchronization, and storage lifecycle."""

    def __init__(
        self,
        minio_storage: MinIOProposalStorage,
        clock: Clock,
        rag_api_url: str = "http://rag-api:8002",
        http_client: Any = None,
    ) -> None:
        self.minio_storage = minio_storage
        self.clock = clock
        self.rag_api_url = rag_api_url.rstrip("/")
        self._http_client = http_client

    @property
    def http_client(self) -> Any:
        if self._http_client is None:
            self._http_client = httpx.Client(timeout=15.0)
        return self._http_client


    def approve_proposal(
        self,
        proposal: Proposal,
        reviewer_id: UUID,
        review_note: str | None = None,
    ) -> Proposal:
        """Transitions proposal to APPROVED and records reviewer details."""
        if proposal.status not in (ProposalStatus.SUBMITTED, ProposalStatus.UNDER_REVIEW):
            raise ValueError(
                f"Cannot approve proposal in '{proposal.status}' state"
            )
        proposal.status = ProposalStatus.APPROVED
        proposal.reviewed_by = reviewer_id
        proposal.reviewed_at = self.clock.now()
        proposal.review_note = review_note
        return proposal

    def reject_proposal(
        self,
        proposal: Proposal,
        reviewer_id: UUID,
        review_note: str | None = None,
    ) -> Proposal:
        """Transitions proposal to REJECTED."""
        if proposal.status not in (ProposalStatus.SUBMITTED, ProposalStatus.UNDER_REVIEW):
            raise ValueError(
                f"Cannot reject proposal in '{proposal.status}' state"
            )
        proposal.status = ProposalStatus.REJECTED
        proposal.reviewed_by = reviewer_id
        proposal.reviewed_at = self.clock.now()
        proposal.review_note = review_note
        return proposal

    def request_revision(
        self,
        proposal: Proposal,
        reviewer_id: UUID,
        review_note: str | None = None,
    ) -> Proposal:
        """Transitions proposal to REVISION_REQUESTED."""
        if proposal.status not in (ProposalStatus.SUBMITTED, ProposalStatus.UNDER_REVIEW):
            raise ValueError(
                f"Cannot request revision for proposal in '{proposal.status}' state"
            )
        proposal.status = ProposalStatus.REVISION_REQUESTED
        proposal.reviewed_by = reviewer_id
        proposal.reviewed_at = self.clock.now()
        proposal.review_note = review_note
        return proposal

    def dispatch_rag_ingest(self, proposal: Proposal) -> bool:
        """Generates presigned URL and triggers RAG API ingestion upon approval."""
        if proposal.status != ProposalStatus.APPROVED:
            raise ValueError("Only APPROVED proposals can be ingested into RAG")

        presigned_url = self.minio_storage.generate_presigned_download_url(
            bucket=proposal.minio_bucket,
            object_key=proposal.minio_key,
            expires_in_seconds=900,  # 15 minutes TTL
        )

        payload = {
            "proposal_id": str(proposal.id),
            "event_id": str(proposal.event_id),
            "club_id": str(proposal.club_id),
            "revision": proposal.revision,
            "presigned_url": presigned_url,
            "title": proposal.title,
            "submitted_by": str(proposal.submitted_by),
            "approved_by": str(proposal.reviewed_by) if proposal.reviewed_by else None,
        }

        url = f"{self.rag_api_url}/v1/ingest/proposal"
        resp = self.http_client.post(url, json=payload)
        if resp.status_code == 200:
            proposal.status = ProposalStatus.CHUNKED
            proposal.rag_ingested_at = self.clock.now()
            return True
        return False

    def is_eligible_for_24h_cleanup(
        self,
        event_concluded_at: datetime | None,
        now: datetime | None = None,
    ) -> bool:
        """Checks whether the event has been in CONCLUDED state for at least 24 hours."""
        if event_concluded_at is None:
            return False
        current_time = now or self.clock.now()
        return (current_time - event_concluded_at) >= timedelta(hours=24)

    def execute_lifecycle_cleanup(
        self,
        proposal: Proposal,
        event_concluded_at: datetime,
        now: datetime | None = None,
    ) -> bool:
        """Executes 24h cleanup: triggers RAG deletion, moves to archive, updates status."""
        if not self.is_eligible_for_24h_cleanup(event_concluded_at, now=now):
            return False

        # 1. Trigger RAG chunk deletion if it was chunked
        if proposal.status == ProposalStatus.CHUNKED:
            delete_url = f"{self.rag_api_url}/v1/ingest/proposal/{proposal.id}"
            resp = self.http_client.request(
                "DELETE",
                delete_url,
                json={"event_id": str(proposal.event_id)},
            )
            if resp.status_code not in (200, 404):
                return False
            proposal.rag_deleted_at = self.clock.now()

        # 2. Archive-move MinIO object (no hard delete)
        self.minio_storage.archive_proposal(
            source_bucket=proposal.minio_bucket,
            source_key=proposal.minio_key,
        )

        proposal.status = ProposalStatus.ARCHIVED
        return True

