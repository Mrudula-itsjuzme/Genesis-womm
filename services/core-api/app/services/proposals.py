"""Submitting, reading and reviewing an event's proposal document (Implementation Plan 07).

A club's organizers submit and read their proposal; only a campus admin reviews it; a delegated
agent does none of it (spine AD-21). Identities come from the signed-in person, every refusal is
audited, and a failing object store or RAG service never leaks detail or undoes a review.
"""

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

import structlog

from app.domain.authz import Action, Actor, Resource, authorize
from app.domain.enums import ProposalStatus
from app.domain.lifecycle import InvalidTransitionError, NotAuthorizedError, TransitionError
from app.domain.time import Clock
from app.services.errors import (
    InvalidRequestError,
    NotFoundError,
    ServiceError,
    StorageUnavailableError,
)
from app.services.ports import (
    AuditRecord,
    IdSource,
    ProposalRecord,
    ProposalStorage,
    ProposalUnitOfWork,
)
from app.services.proposal_lifecycle import PRESIGNED_URL_TTL_SECONDS, ProposalLifecycleManager
from app.services.schedule_write import RequestContext, refusal_code

log = structlog.get_logger(__name__)

MAX_PROPOSAL_BYTES = 10 * 1024 * 1024
TITLE_MAX = 255
_PDF_MAGIC = b"%PDF-"


class ReviewAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    REQUEST_REVISION = "request_revision"


@dataclass(frozen=True)
class DownloadLink:
    url: str
    expires_in_seconds: int


class ProposalService:
    def __init__(
        self,
        uow_factory: Callable[[], ProposalUnitOfWork],
        *,
        storage: ProposalStorage,
        manager: ProposalLifecycleManager,
        clock: Clock,
        ids: IdSource,
    ) -> None:
        self._uow_factory = uow_factory
        self._storage = storage
        self._manager = manager
        self._clock = clock
        self._ids = ids

    # ---- submitting ----

    def submit(
        self, ctx: RequestContext, *, club_id: UUID, event_id: UUID, title: str, content: bytes
    ) -> ProposalRecord:
        try:
            return self._submit(ctx, club_id, event_id, title, content)
        except (ServiceError, TransitionError) as refusal:
            self._record_refusal(ctx, "SUBMIT_PROPOSAL", None, refusal)
            raise

    def _submit(
        self, ctx: RequestContext, club_id: UUID, event_id: UUID, title: str, content: bytes
    ) -> ProposalRecord:
        self._require(ctx.actor, Action.SUBMIT_PROPOSAL, club_id)
        clean_title = _clean_title(title)
        _check_document(content)

        with self._uow_factory() as uow:
            event = uow.events.get(event_id)
            if event is None or event.club_id != club_id:
                raise NotFoundError("event", event_id)
            revision = uow.proposals.next_revision(event_id)
        proposal_id = self._ids.new_id()

        # The file goes up between the two short transactions, so no transaction is held open
        # across network I/O.
        try:
            bucket, key, size, digest = self._storage.upload_proposal(
                club_id=club_id,
                event_id=event_id,
                proposal_id=proposal_id,
                revision=revision,
                file_bytes=content,
                content_type="application/pdf",
            )
        except Exception as error:
            raise StorageUnavailableError(f"upload failed: {type(error).__name__}") from error

        now = self._clock.now()
        record = ProposalRecord(
            id=proposal_id,
            event_id=event_id,
            club_id=club_id,
            submitted_by=ctx.actor.user_id,
            title=clean_title,
            minio_bucket=bucket,
            minio_key=key,
            submitted_at=now,
            revision=revision,
            file_size_bytes=size,
            sha256_hash=digest,
        )
        with self._uow_factory() as uow:
            uow.proposals.add(record)
            uow.audit.add(self._audit(ctx, "SUBMIT_PROPOSAL", proposal_id, "SUCCESS", None, now))
            uow.commit()
        return record

    # ---- reading ----

    def get(self, actor: Actor, proposal_id: UUID) -> ProposalRecord:
        with self._uow_factory() as uow:
            record = self._load(uow, proposal_id)
        self._require(actor, Action.VIEW_PROPOSAL, record.club_id)
        return record

    def download_url(self, ctx: RequestContext, proposal_id: UUID) -> DownloadLink:
        try:
            return self._download_url(ctx, proposal_id)
        except (ServiceError, TransitionError) as refusal:
            self._record_refusal(ctx, "DOWNLOAD_PROPOSAL", proposal_id, refusal)
            raise

    def _download_url(self, ctx: RequestContext, proposal_id: UUID) -> DownloadLink:
        with self._uow_factory() as uow:
            record = self._load(uow, proposal_id)
            self._require(ctx.actor, Action.VIEW_PROPOSAL, record.club_id)
            try:
                url = self._storage.generate_presigned_download_url(
                    bucket=record.minio_bucket,
                    object_key=record.minio_key,
                    expires_in_seconds=PRESIGNED_URL_TTL_SECONDS,
                )
            except Exception as error:
                raise StorageUnavailableError(f"presign failed: {type(error).__name__}") from error
            uow.audit.add(
                self._audit(
                    ctx, "DOWNLOAD_PROPOSAL", proposal_id, "SUCCESS", None, self._clock.now()
                )
            )
            uow.commit()
        return DownloadLink(url, PRESIGNED_URL_TTL_SECONDS)

    # ---- reviewing ----

    def review(
        self,
        ctx: RequestContext,
        proposal_id: UUID,
        action: ReviewAction,
        review_note: str | None,
    ) -> ProposalRecord:
        try:
            record = self._review(ctx, proposal_id, action, review_note)
        except (ServiceError, TransitionError) as refusal:
            self._record_refusal(ctx, "REVIEW_PROPOSAL", proposal_id, refusal)
            raise
        if action is ReviewAction.APPROVE:
            record = self._hand_to_rag(ctx, record)
        return record

    def _review(
        self,
        ctx: RequestContext,
        proposal_id: UUID,
        action: ReviewAction,
        review_note: str | None,
    ) -> ProposalRecord:
        self._require(ctx.actor, Action.REVIEW_PROPOSAL, None)
        with self._uow_factory() as uow:
            record = self._load(uow, proposal_id)
            before = record.status
            decide = {
                ReviewAction.APPROVE: self._manager.approve_proposal,
                ReviewAction.REJECT: self._manager.reject_proposal,
                ReviewAction.REQUEST_REVISION: self._manager.request_revision,
            }[action]
            decide(record, reviewer_id=ctx.actor.user_id, review_note=review_note)
            if not uow.proposals.save(record, expected_status=before):
                # Someone decided it between our read and our write.
                current = uow.proposals.get(proposal_id)
                raise InvalidTransitionError(
                    before if current is None else current.status, record.status
                )
            uow.audit.add(
                self._audit(ctx, "REVIEW_PROPOSAL", proposal_id, "SUCCESS", None, self._clock.now())
            )
            uow.commit()
        return record

    def _hand_to_rag(self, ctx: RequestContext, record: ProposalRecord) -> ProposalRecord:
        """Best effort, after the review is committed: RAG or storage being down never undoes it."""
        try:
            accepted = self._manager.dispatch_rag_ingest(record)
        except Exception as error:
            log.warning("rag_handoff_failed", proposal_id=str(record.id), kind=type(error).__name__)
            record.status = ProposalStatus.APPROVED
            return record
        if not accepted:
            return record
        with self._uow_factory() as uow:
            if uow.proposals.save(record, expected_status=ProposalStatus.APPROVED):
                uow.audit.add(
                    self._audit(
                        ctx, "INGEST_PROPOSAL", record.id, "SUCCESS", None, self._clock.now()
                    )
                )
                uow.commit()
        return record

    # ---- shared ----

    @staticmethod
    def _require(actor: Actor, action: Action, club_id: UUID | None) -> None:
        decision = authorize(actor, action, Resource(club_id=club_id))
        if not decision.allowed:
            raise NotAuthorizedError(decision)

    def _load(self, uow: ProposalUnitOfWork, proposal_id: UUID) -> ProposalRecord:
        record = uow.proposals.get(proposal_id)
        if record is None:
            raise NotFoundError("proposal", proposal_id)
        return record

    def _audit(
        self,
        ctx: RequestContext,
        action: str,
        entity_id: UUID | None,
        outcome: str,
        reason_code: str | None,
        now: datetime,
    ) -> AuditRecord:
        return AuditRecord(
            id=self._ids.new_id(),
            actor_id=ctx.actor.user_id,
            action=action,
            entity_type="proposal",
            entity_id=entity_id,
            outcome=outcome,
            reason_code=reason_code,
            request_id=ctx.request_id,
            via="AGENT" if ctx.actor.via_agent else "USER",
            created_at=now,
        )

    def _record_refusal(
        self, ctx: RequestContext, action: str, entity_id: UUID | None, error: Exception
    ) -> None:
        """Audit a refusal in its own transaction; it must never hide the refusal itself."""
        try:
            now = self._clock.now()
            with self._uow_factory() as uow:
                uow.audit.add(
                    self._audit(ctx, action, entity_id, "REFUSED", refusal_code(error), now)
                )
                uow.commit()
        except Exception:
            with suppress(Exception):
                log.warning("refusal_audit_failed", action=action, request_id=ctx.request_id)


def _clean_title(title: str) -> str:
    cleaned = title.strip()
    if not cleaned or len(cleaned) > TITLE_MAX:
        raise InvalidRequestError(f"title must be 1 to {TITLE_MAX} characters")
    return cleaned


def _check_document(content: bytes) -> None:
    if not content:
        raise InvalidRequestError("the proposal file is empty")
    if len(content) > MAX_PROPOSAL_BYTES:
        raise InvalidRequestError(f"the proposal file is larger than {MAX_PROPOSAL_BYTES} bytes")
    if not content.startswith(_PDF_MAGIC):
        raise InvalidRequestError("the proposal file must be a PDF")
