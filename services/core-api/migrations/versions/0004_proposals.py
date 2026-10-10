"""Event proposal documents and their review.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "core"


def _ts() -> sa.types.TypeEngine[object]:
    return sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("club_id", sa.Uuid(), nullable=False),
        sa.Column("submitted_by", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("minio_bucket", sa.String(128), nullable=False),
        sa.Column("minio_key", sa.String(512), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("sha256_hash", sa.String(64), nullable=True),
        sa.Column("submitted_at", _ts(), nullable=False),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", _ts(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("rag_ingested_at", _ts(), nullable=True),
        sa.Column("rag_deleted_at", _ts(), nullable=True),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', 'REJECTED', "
            "'REVISION_REQUESTED', 'CHUNKED', 'ARCHIVED')",
            name="status",
        ),
        sa.CheckConstraint("revision >= 1", name="revision_positive"),
        sa.CheckConstraint("length(trim(title)) > 0", name="title_not_blank"),
        sa.CheckConstraint(
            "file_size_bytes IS NULL OR file_size_bytes >= 0", name="size_non_negative"
        ),
        sa.CheckConstraint(
            "sha256_hash IS NULL OR length(sha256_hash) = 64", name="sha256_length"
        ),
        sa.CheckConstraint(
            "status NOT IN ('APPROVED', 'REJECTED', 'REVISION_REQUESTED', 'CHUNKED') "
            "OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
            name="decided_has_reviewer",
        ),
        sa.CheckConstraint(
            "status <> 'CHUNKED' OR rag_ingested_at IS NOT NULL",
            name="chunked_has_ingest_time",
        ),
        sa.ForeignKeyConstraint(["event_id"], [f"{SCHEMA}.events.id"]),
        sa.ForeignKeyConstraint(["club_id"], [f"{SCHEMA}.clubs.id"]),
        sa.ForeignKeyConstraint(["submitted_by"], [f"{SCHEMA}.users.id"]),
        sa.ForeignKeyConstraint(["reviewed_by"], [f"{SCHEMA}.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index("ix_proposals_event_id", "proposals", ["event_id"], schema=SCHEMA)
    op.create_index("ix_proposals_club_id", "proposals", ["club_id"], schema=SCHEMA)
    op.create_index("ix_proposals_status", "proposals", ["status"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("proposals", schema=SCHEMA)
