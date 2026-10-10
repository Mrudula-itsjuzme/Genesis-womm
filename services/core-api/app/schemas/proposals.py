from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.domain.enums import ProposalStatus


class ProposalUploadOut(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    event_id: UUID
    club_id: UUID
    revision: int = Field(ge=1)
    status: ProposalStatus
    title: str
    minio_key: str
    file_size_bytes: int | None = None
    submitted_at: datetime


class ProposalStatusPatch(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    action: Literal["approve", "reject", "request_revision"]
    review_note: str | None = Field(default=None, max_length=2000)


class ProposalDownloadUrlOut(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    download_url: str
    expires_in_seconds: int = 900


class ProposalOut(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: UUID
    event_id: UUID
    club_id: UUID
    submitted_by: UUID
    revision: int
    status: ProposalStatus
    title: str
    minio_bucket: str
    minio_key: str
    file_size_bytes: int | None = None
    sha256_hash: str | None = None
    submitted_at: datetime
    reviewed_by: UUID | None = None
    reviewed_at: datetime | None = None
    review_note: str | None = None
    rag_ingested_at: datetime | None = None
    rag_deleted_at: datetime | None = None
