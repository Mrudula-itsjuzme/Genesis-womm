"""Agent proposals awaiting a human decision.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-11
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "core"


def _ts() -> sa.types.TypeEngine[object]:
    return sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "agent_actions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("summary", sa.String(300), nullable=False),
        sa.Column("requested_by", sa.Uuid(), nullable=False),
        sa.Column("club_id", sa.Uuid(), nullable=False),
        sa.Column("target_event_id", sa.Uuid(), nullable=True),
        sa.Column("expected_revision", sa.Integer(), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column(
            "conflicts",
            postgresql.JSONB(),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("decided_by", sa.Uuid(), nullable=True),
        sa.Column("decided_at", _ts(), nullable=True),
        sa.Column("result_entity_type", sa.String(40), nullable=True),
        sa.Column("result_entity_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", _ts(), nullable=False),
        sa.Column("updated_at", _ts(), nullable=False),
        sa.CheckConstraint(
            "type IN ('CREATE_EVENT_DRAFT', 'REQUEST_EVENT_CHANGE', 'RECORD_COMMITMENT', "
            "'CREATE_FOLLOWUP_DRAFT')",
            name="type",
        ),
        sa.CheckConstraint(
            "status IN ('PROPOSED', 'EXECUTED', 'REJECTED', 'EXPIRED')", name="status"
        ),
        sa.CheckConstraint("length(trim(summary)) > 0", name="summary_not_blank"),
        sa.CheckConstraint(
            "expected_revision IS NULL OR expected_revision >= 1",
            name="expected_revision_positive",
        ),
        sa.CheckConstraint(
            "status <> 'PROPOSED' OR (decided_by IS NULL AND decided_at IS NULL "
            "AND result_entity_type IS NULL AND result_entity_id IS NULL)",
            name="proposed_is_undecided",
        ),
        sa.CheckConstraint(
            "status <> 'EXECUTED' OR (decided_by IS NOT NULL AND decided_at IS NOT NULL "
            "AND result_entity_type IS NOT NULL AND result_entity_id IS NOT NULL)",
            name="executed_has_result",
        ),
        sa.CheckConstraint(
            "status <> 'REJECTED' OR (decided_by IS NOT NULL AND decided_at IS NOT NULL)",
            name="rejected_has_decision",
        ),
        sa.ForeignKeyConstraint(["requested_by"], [f"{SCHEMA}.users.id"]),
        sa.ForeignKeyConstraint(["club_id"], [f"{SCHEMA}.clubs.id"]),
        sa.ForeignKeyConstraint(["target_event_id"], [f"{SCHEMA}.events.id"]),
        sa.ForeignKeyConstraint(["decided_by"], [f"{SCHEMA}.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_agent_actions_requested_by_created_at",
        "agent_actions",
        ["requested_by", "created_at"],
        schema=SCHEMA,
    )
    op.create_index(
        "ix_agent_actions_target_event_id", "agent_actions", ["target_event_id"], schema=SCHEMA
    )
    op.create_index("ix_agent_actions_status", "agent_actions", ["status"], schema=SCHEMA)


def downgrade() -> None:
    op.drop_table("agent_actions", schema=SCHEMA)
