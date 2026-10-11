"""Persist creator-owned shared resource interest requests."""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resource_interests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("requester_id", sa.Uuid(), nullable=False),
        sa.Column("category", sa.String(60), nullable=False),
        sa.Column("purpose", sa.String(160), nullable=False),
        sa.Column("preferred_date", sa.Date(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("requirements", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("start_time < end_time", name="start_before_end"),
        sa.ForeignKeyConstraint(["requester_id"], ["core.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema="core",
    )
    op.create_index(
        "ix_core_resource_interests_requester_id",
        "resource_interests",
        ["requester_id"],
        schema="core",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_core_resource_interests_requester_id",
        table_name="resource_interests",
        schema="core",
    )
    op.drop_table("resource_interests", schema="core")
