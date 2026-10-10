"""An event's proposal document and its review (Implementation Plan 07, spine AD-20).

The PDF lives in object storage; this row points at it and records who submitted it, who
reviewed it and when RAG took or dropped it. The database refuses a decided proposal that names
no reviewer, and a RAG-ingested one that does not say when.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import ProposalStatus
from app.models.base import Base
from app.models.directory import Timestamp, in_values


class ProposalRow(Base):
    __tablename__ = "proposals"
    __table_args__ = (
        CheckConstraint(in_values("status", ProposalStatus), name="status"),
        CheckConstraint("revision >= 1", name="revision_positive"),
        CheckConstraint("length(trim(title)) > 0", name="title_not_blank"),
        CheckConstraint(
            "file_size_bytes IS NULL OR file_size_bytes >= 0", name="size_non_negative"
        ),
        CheckConstraint("sha256_hash IS NULL OR length(sha256_hash) = 64", name="sha256_length"),
        CheckConstraint(
            "status NOT IN ('APPROVED', 'REJECTED', 'REVISION_REQUESTED', 'CHUNKED') "
            "OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="decided_has_reviewer",
        ),
        CheckConstraint(
            "status <> 'CHUNKED' OR rag_ingested_at IS NOT NULL",
            name="chunked_has_ingest_time",
        ),
        Index("ix_proposals_event_id", "event_id"),
        Index("ix_proposals_club_id", "club_id"),
        Index("ix_proposals_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"))
    club_id: Mapped[UUID] = mapped_column(ForeignKey("clubs.id"))
    submitted_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    revision: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(255))
    minio_bucket: Mapped[str] = mapped_column(String(128))
    minio_key: Mapped[str] = mapped_column(String(512))
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger)
    sha256_hash: Mapped[str | None] = mapped_column(String(64))
    submitted_at: Mapped[datetime] = mapped_column(Timestamp)
    reviewed_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    reviewed_at: Mapped[datetime | None] = mapped_column(Timestamp)
    review_note: Mapped[str | None] = mapped_column(Text)
    rag_ingested_at: Mapped[datetime | None] = mapped_column(Timestamp)
    rag_deleted_at: Mapped[datetime | None] = mapped_column(Timestamp)
