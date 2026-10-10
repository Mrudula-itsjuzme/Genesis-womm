"""SQLAlchemy model for event proposals stored in MinIO and indexed into RAG upon approval."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import ProposalStatus
from app.models.base import Base


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    event_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    club_id: Mapped[UUID] = mapped_column(nullable=False, index=True)
    submitted_by: Mapped[UUID] = mapped_column(nullable=False)
    revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[ProposalStatus] = mapped_column(
        SQLEnum(ProposalStatus, native_enum=False, name="proposal_status"),
        nullable=False,
        default=ProposalStatus.SUBMITTED,
    )


    title: Mapped[str] = mapped_column(String(255), nullable=False)
    minio_bucket: Mapped[str] = mapped_column(String(128), nullable=False)
    minio_key: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    reviewed_by: Mapped[UUID | None] = mapped_column(nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    rag_ingested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rag_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __init__(
        self,

        event_id: UUID,
        club_id: UUID,
        submitted_by: UUID,
        title: str,
        minio_bucket: str,
        minio_key: str,
        id: UUID | None = None,
        revision: int = 1,
        status: ProposalStatus = ProposalStatus.SUBMITTED,
        file_size_bytes: int | None = None,
        sha256_hash: str | None = None,
        submitted_at: datetime | None = None,
        reviewed_by: UUID | None = None,
        reviewed_at: datetime | None = None,
        review_note: str | None = None,
        rag_ingested_at: datetime | None = None,
        rag_deleted_at: datetime | None = None,
    ) -> None:
        self.id = id or uuid4()
        self.event_id = event_id
        self.club_id = club_id
        self.submitted_by = submitted_by
        self.title = title
        self.minio_bucket = minio_bucket
        self.minio_key = minio_key
        self.revision = revision
        self.status = status
        self.file_size_bytes = file_size_bytes
        self.sha256_hash = sha256_hash
        self.submitted_at = submitted_at or datetime.now(UTC)
        self.reviewed_by = reviewed_by
        self.reviewed_at = reviewed_at
        self.review_note = review_note
        self.rag_ingested_at = rag_ingested_at
        self.rag_deleted_at = rag_deleted_at

