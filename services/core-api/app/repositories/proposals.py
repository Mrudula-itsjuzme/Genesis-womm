"""PostgreSQL adapter for event proposals (Implementation Plan 07).

``save`` is a single compare-and-set statement, so two reviewers (or two retries) moving the
same proposal cannot both win.
"""

from typing import cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.domain.enums import ProposalStatus
from app.models.proposal import ProposalRow
from app.services.ports import ProposalRecord


def _to_record(row: ProposalRow) -> ProposalRecord:
    return ProposalRecord(
        id=row.id,
        event_id=row.event_id,
        club_id=row.club_id,
        submitted_by=row.submitted_by,
        title=row.title,
        minio_bucket=row.minio_bucket,
        minio_key=row.minio_key,
        submitted_at=row.submitted_at,
        revision=row.revision,
        status=ProposalStatus(row.status),
        file_size_bytes=row.file_size_bytes,
        sha256_hash=row.sha256_hash,
        reviewed_by=row.reviewed_by,
        reviewed_at=row.reviewed_at,
        review_note=row.review_note,
        rag_ingested_at=row.rag_ingested_at,
        rag_deleted_at=row.rag_deleted_at,
    )


class SqlProposalStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, proposal_id: UUID) -> ProposalRecord | None:
        row = self._session.scalars(
            select(ProposalRow)
            .where(ProposalRow.id == proposal_id)
            .execution_options(populate_existing=True)
        ).first()
        return None if row is None else _to_record(row)

    def add(self, record: ProposalRecord) -> None:
        self._session.add(
            ProposalRow(
                id=record.id,
                event_id=record.event_id,
                club_id=record.club_id,
                submitted_by=record.submitted_by,
                revision=record.revision,
                status=record.status.value,
                title=record.title,
                minio_bucket=record.minio_bucket,
                minio_key=record.minio_key,
                file_size_bytes=record.file_size_bytes,
                sha256_hash=record.sha256_hash,
                submitted_at=record.submitted_at,
                reviewed_by=record.reviewed_by,
                reviewed_at=record.reviewed_at,
                review_note=record.review_note,
                rag_ingested_at=record.rag_ingested_at,
                rag_deleted_at=record.rag_deleted_at,
            )
        )
        self._session.flush()

    def next_revision(self, event_id: UUID) -> int:
        latest = self._session.scalar(
            select(func.max(ProposalRow.revision)).where(ProposalRow.event_id == event_id)
        )
        return int(latest or 0) + 1

    def save(self, record: ProposalRecord, *, expected_status: ProposalStatus) -> bool:
        result = cast(
            CursorResult[tuple[()]],
            self._session.execute(
                update(ProposalRow)
                .where(
                    ProposalRow.id == record.id,
                    ProposalRow.status == expected_status.value,
                )
                .values(
                    status=record.status.value,
                    reviewed_by=record.reviewed_by,
                    reviewed_at=record.reviewed_at,
                    review_note=record.review_note,
                    rag_ingested_at=record.rag_ingested_at,
                    rag_deleted_at=record.rag_deleted_at,
                )
                .execution_options(synchronize_session=False)
            ),
        )
        return result.rowcount == 1
