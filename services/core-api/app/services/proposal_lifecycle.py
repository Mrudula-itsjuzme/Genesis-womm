"""How a proposal moves through review and into, and out of, RAG (Implementation Plan 07).

Pure orchestration over a ``ProposalRecord``: it decides what may happen next and says when, and
reaches object storage and the RAG service only through ports. Saving the result is the caller's
job, so a review and its save can share one transaction.
"""

from datetime import datetime, timedelta
from uuid import UUID

from app.domain.enums import ProposalStatus
from app.domain.lifecycle import InvalidTransitionError
from app.domain.time import Clock
from app.services.ports import ProposalRecord, ProposalStorage, RagIngest

_AWAITING_REVIEW = (ProposalStatus.SUBMITTED, ProposalStatus.UNDER_REVIEW)
PRESIGNED_URL_TTL_SECONDS = 900  # fifteen minutes: RAG fetches the file once, straight away
CLEANUP_AFTER = timedelta(hours=24)


class ProposalLifecycleManager:
    """Coordinates proposal state transitions, RAG synchronization and storage lifecycle."""

    def __init__(self, storage: ProposalStorage, rag: RagIngest, clock: Clock) -> None:
        self._storage = storage
        self._rag = rag
        self._clock = clock

    def approve_proposal(
        self, proposal: ProposalRecord, reviewer_id: UUID, review_note: str | None = None
    ) -> ProposalRecord:
        return self._decide(proposal, ProposalStatus.APPROVED, reviewer_id, review_note)

    def reject_proposal(
        self, proposal: ProposalRecord, reviewer_id: UUID, review_note: str | None = None
    ) -> ProposalRecord:
        return self._decide(proposal, ProposalStatus.REJECTED, reviewer_id, review_note)

    def request_revision(
        self, proposal: ProposalRecord, reviewer_id: UUID, review_note: str | None = None
    ) -> ProposalRecord:
        return self._decide(proposal, ProposalStatus.REVISION_REQUESTED, reviewer_id, review_note)

    def _decide(
        self,
        proposal: ProposalRecord,
        outcome: ProposalStatus,
        reviewer_id: UUID,
        review_note: str | None,
    ) -> ProposalRecord:
        if proposal.status not in _AWAITING_REVIEW:
            raise InvalidTransitionError(proposal.status, outcome)
        proposal.status = outcome
        proposal.reviewed_by = reviewer_id
        proposal.reviewed_at = self._clock.now()
        proposal.review_note = review_note
        return proposal

    def dispatch_rag_ingest(self, proposal: ProposalRecord) -> bool:
        """Hand an approved proposal to RAG. False leaves it APPROVED so it can be retried."""
        if proposal.status != ProposalStatus.APPROVED:
            raise ValueError("Only APPROVED proposals can be ingested into RAG")
        presigned_url = self._storage.generate_presigned_download_url(
            bucket=proposal.minio_bucket,
            object_key=proposal.minio_key,
            expires_in_seconds=PRESIGNED_URL_TTL_SECONDS,
        )
        accepted = self._rag.ingest(
            {
                "proposal_id": str(proposal.id),
                "event_id": str(proposal.event_id),
                "club_id": str(proposal.club_id),
                "revision": proposal.revision,
                "presigned_url": presigned_url,
                "title": proposal.title,
                "submitted_by": str(proposal.submitted_by),
                "approved_by": str(proposal.reviewed_by) if proposal.reviewed_by else None,
            }
        )
        if accepted:
            proposal.status = ProposalStatus.CHUNKED
            proposal.rag_ingested_at = self._clock.now()
        return accepted

    def is_eligible_for_24h_cleanup(
        self, event_concluded_at: datetime | None, now: datetime | None = None
    ) -> bool:
        """True once the event has been over for at least 24 hours."""
        if event_concluded_at is None:
            return False
        return ((now or self._clock.now()) - event_concluded_at) >= CLEANUP_AFTER

    def execute_lifecycle_cleanup(
        self,
        proposal: ProposalRecord,
        event_concluded_at: datetime,
        now: datetime | None = None,
    ) -> bool:
        """Make RAG forget the proposal, then archive the file. Both, in that order, or neither."""
        if not self.is_eligible_for_24h_cleanup(event_concluded_at, now=now):
            return False
        if proposal.status == ProposalStatus.CHUNKED:
            if not self._rag.delete(proposal.id, proposal.event_id):
                return False  # RAG still serves it, so the file must stay
            proposal.rag_deleted_at = self._clock.now()
        self._storage.archive_proposal(
            source_bucket=proposal.minio_bucket, source_key=proposal.minio_key
        )
        proposal.status = ProposalStatus.ARCHIVED
        return True
