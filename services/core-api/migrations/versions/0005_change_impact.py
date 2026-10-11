"""Persist staged changes and explicit operational dependencies."""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
SCHEMA = "core"


def upgrade() -> None:
    op.create_table(
        "event_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("core.events.id"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("needs_revalidation", sa.Boolean(), nullable=False),
        sa.Column("reported_by", sa.Uuid(), sa.ForeignKey("core.users.id"), nullable=False),
        sa.Column("verified_by", sa.Uuid(), sa.ForeignKey("core.users.id")),
        sa.Column("verified_at", sa.DateTime(timezone=True)),
        sa.Column("evidence_id", sa.Uuid(), sa.ForeignKey("core.evidence_records.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_id", "id", name="uq_event_items_event_id_id"),
        sa.CheckConstraint("kind IN ('COMMITMENT', 'TASK')", name="kind"),
        sa.CheckConstraint("length(trim(title)) > 0", name="title_not_blank"),
        sa.CheckConstraint(
            "(kind = 'TASK' AND status IN ('OPEN', 'CLOSED')) OR "
            "(kind = 'COMMITMENT' AND status IN ('DRAFT', 'REQUESTED', 'ACKNOWLEDGED', "
            "'CONDITIONALLY_CONFIRMED', 'CONFIRMED', 'NEEDS_REVALIDATION', 'CLOSED'))",
            name="status",
        ),
        sa.CheckConstraint(
            "status <> 'CONFIRMED' OR (verified_by IS NOT NULL AND verified_at IS NOT NULL "
            "AND evidence_id IS NOT NULL)",
            name="confirmed_is_verified",
        ),
        schema=SCHEMA,
    )
    op.create_index("ix_core_event_items_event_id", "event_items", ["event_id"], schema=SCHEMA)
    op.create_table(
        "event_dependencies",
        sa.Column("event_id", sa.Uuid(), primary_key=True),
        sa.Column("dependent_id", sa.Uuid(), primary_key=True),
        sa.Column("field_path", sa.String(40), primary_key=True),
        sa.Column("rule_id", sa.String(40), nullable=False),
        sa.ForeignKeyConstraint(
            ["event_id", "dependent_id"], ["core.event_items.event_id", "core.event_items.id"]
        ),
        sa.CheckConstraint(
            "field_path IN ('start_at', 'end_at', 'resource_id', 'expected_attendance')",
            name="field_path",
        ),
        sa.CheckConstraint("rule_id = 'FIELD_CHANGE'", name="rule_id"),
        schema=SCHEMA,
    )
    op.create_table(
        "change_proposals",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("event_id", sa.Uuid(), sa.ForeignKey("core.events.id"), nullable=False),
        sa.Column("base_revision", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("changes", JSONB(), nullable=False),
        sa.Column("conflicts", JSONB(), nullable=False),
        sa.Column("impact", JSONB(), nullable=False),
        sa.Column("requested_by", sa.Uuid(), sa.ForeignKey("core.users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("applied_by", sa.Uuid(), sa.ForeignKey("core.users.id")),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("base_revision >= 1", name="base_revision_positive"),
        sa.CheckConstraint("status IN ('STAGED', 'APPLIED')", name="status"),
        sa.CheckConstraint("length(trim(reason)) > 0", name="reason_not_blank"),
        sa.CheckConstraint(
            "status <> 'APPLIED' OR (applied_by IS NOT NULL AND applied_at IS NOT NULL)",
            name="applied_has_actor",
        ),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_core_change_proposals_event_id", "change_proposals", ["event_id"], schema=SCHEMA
    )


def downgrade() -> None:
    op.drop_table("change_proposals", schema=SCHEMA)
    op.drop_table("event_dependencies", schema=SCHEMA)
    op.drop_table("event_items", schema=SCHEMA)
