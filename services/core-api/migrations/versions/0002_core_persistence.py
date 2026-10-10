"""Persistence for events and their history.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "core"
HISTORY_TABLES = ("event_revisions", "audit_events", "evidence_records")


def _ts() -> sa.types.TypeEngine[object]:
    return sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(320), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("campus_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("created_at", _ts(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        schema=SCHEMA,
    )
    op.create_table(
        "clubs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("created_at", _ts(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
        schema=SCHEMA,
    )
    op.create_table(
        "memberships",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("club_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("created_at", _ts(), nullable=False),
        sa.CheckConstraint("role IN ('ORGANIZER', 'CLUB_ADMIN')", name="club_role"),
        sa.ForeignKeyConstraint(["user_id"], [f"{SCHEMA}.users.id"]),
        sa.ForeignKeyConstraint(["club_id"], [f"{SCHEMA}.clubs.id"]),
        sa.PrimaryKeyConstraint("user_id", "club_id"),
        schema=SCHEMA,
    )
    op.create_table(
        "resources",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(200), nullable=True),
        sa.Column("capacity", sa.Integer(), nullable=True),
        sa.Column(
            "availability_state", sa.String(20), server_default=sa.text("'UNKNOWN'"), nullable=False
        ),
        sa.Column(
            "freshness_state", sa.String(20), server_default=sa.text("'UNKNOWN'"), nullable=False
        ),
        sa.Column("source_id", sa.String(100), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("collected_at", _ts(), nullable=True),
        sa.Column("last_checked_at", _ts(), nullable=True),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("created_at", _ts(), nullable=False),
        sa.CheckConstraint("kind IN ('VENUE', 'EQUIPMENT', 'SERVICE')", name="kind"),
        sa.CheckConstraint(
            "availability_state IN ('UNKNOWN', 'REQUESTED', 'CONFIRMED')", name="availability"
        ),
        sa.CheckConstraint(
            "freshness_state IN ('CURRENT', 'STALE', 'HISTORICAL', 'PARSE_FAILED', "
            "'REVIEW_REQUIRED', 'UNKNOWN')",
            name="freshness",
        ),
        sa.CheckConstraint("capacity IS NULL OR capacity >= 0", name="capacity_non_negative"),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_table(
        "evidence_records",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("reference", sa.Text(), nullable=False),
        sa.Column("issuer", sa.String(200), nullable=True),
        sa.Column("captured_at", _ts(), nullable=False),
        sa.Column("recorded_by", sa.Uuid(), nullable=False),
        sa.Column("created_at", _ts(), nullable=False),
        sa.ForeignKeyConstraint(["recorded_by"], [f"{SCHEMA}.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_table(
        "events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("club_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("start_at", _ts(), nullable=False),
        sa.Column("end_at", _ts(), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=True),
        sa.Column("expected_attendance", sa.Integer(), nullable=True),
        sa.Column(
            "audience_tags",
            postgresql.ARRAY(sa.String(40)),
            server_default=sa.text("'{}'"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("verified_by", sa.Uuid(), nullable=True),
        sa.Column("verified_at", _ts(), nullable=True),
        sa.Column("evidence_id", sa.Uuid(), nullable=True),
        sa.Column("is_synthetic", sa.Boolean(), nullable=False),
        sa.Column("created_at", _ts(), nullable=False),
        sa.Column("updated_at", _ts(), nullable=False),
        sa.CheckConstraint("start_at < end_at", name="start_before_end"),
        sa.CheckConstraint(
            "status IN ('DRAFT', 'PROPOSED', 'SUBMITTED', 'CONFIRMED', 'COMPLETED', "
            "'REJECTED', 'CANCELLED')",
            name="status",
        ),
        sa.CheckConstraint("revision >= 1", name="revision_positive"),
        sa.CheckConstraint(
            "expected_attendance IS NULL OR expected_attendance >= 0",
            name="attendance_non_negative",
        ),
        sa.CheckConstraint(
            "status <> 'CONFIRMED' OR (verified_by IS NOT NULL AND verified_at IS NOT NULL "
            "AND evidence_id IS NOT NULL)",
            name="confirmed_is_verified",
        ),
        sa.ForeignKeyConstraint(["club_id"], [f"{SCHEMA}.clubs.id"]),
        sa.ForeignKeyConstraint(["resource_id"], [f"{SCHEMA}.resources.id"]),
        sa.ForeignKeyConstraint(["created_by"], [f"{SCHEMA}.users.id"]),
        sa.ForeignKeyConstraint(["verified_by"], [f"{SCHEMA}.users.id"]),
        sa.ForeignKeyConstraint(["evidence_id"], [f"{SCHEMA}.evidence_records.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_events_resource_id_start_at", "events", ["resource_id", "start_at"], schema=SCHEMA
    )
    op.create_index("ix_events_club_id", "events", ["club_id"], schema=SCHEMA)
    op.create_index("ix_events_status", "events", ["status"], schema=SCHEMA)

    op.create_table(
        "event_revisions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("previous", postgresql.JSONB(), nullable=True),
        sa.Column("current", postgresql.JSONB(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("created_at", _ts(), nullable=False),
        sa.CheckConstraint("revision >= 1", name="revision_positive"),
        sa.ForeignKeyConstraint(["event_id"], [f"{SCHEMA}.events.id"]),
        sa.ForeignKeyConstraint(["actor_id"], [f"{SCHEMA}.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("event_id", "revision", name="uq_event_revisions_event_revision"),
        schema=SCHEMA,
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("entity_type", sa.String(40), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("outcome", sa.String(40), nullable=False),
        sa.Column("reason_code", sa.String(60), nullable=True),
        sa.Column("request_id", sa.String(128), nullable=False),
        sa.Column("via", sa.String(10), nullable=False),
        sa.Column("created_at", _ts(), nullable=False),
        sa.CheckConstraint("via IN ('USER', 'AGENT')", name="via"),
        sa.ForeignKeyConstraint(["actor_id"], [f"{SCHEMA}.users.id"]),
        sa.PrimaryKeyConstraint("id"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_audit_events_entity", "audit_events", ["entity_type", "entity_id"], schema=SCHEMA
    )
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"], schema=SCHEMA)

    op.create_table(
        "idempotency_keys",
        sa.Column("actor_id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(128), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("response", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", _ts(), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], [f"{SCHEMA}.users.id"]),
        sa.PrimaryKeyConstraint("actor_id", "key"),
        schema=SCHEMA,
    )
    op.create_table(
        "schedule_overrides",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scope", sa.String(20), nullable=False),
        sa.Column("event_a_id", sa.Uuid(), nullable=False),
        sa.Column("event_b_id", sa.Uuid(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("authorized_by", sa.Uuid(), nullable=False),
        sa.Column("evidence_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", _ts(), nullable=False),
        sa.CheckConstraint("scope IN ('CAMPUS_GAP', 'VENUE_OVERLAP')", name="scope"),
        sa.CheckConstraint("event_a_id < event_b_id", name="pair_order"),
        sa.CheckConstraint("length(trim(reason)) > 0", name="reason_not_blank"),
        sa.ForeignKeyConstraint(["event_a_id"], [f"{SCHEMA}.events.id"]),
        sa.ForeignKeyConstraint(["event_b_id"], [f"{SCHEMA}.events.id"]),
        sa.ForeignKeyConstraint(["authorized_by"], [f"{SCHEMA}.users.id"]),
        sa.ForeignKeyConstraint(["evidence_id"], [f"{SCHEMA}.evidence_records.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "scope", "event_a_id", "event_b_id", name="uq_schedule_overrides_pair_scope"
        ),
        schema=SCHEMA,
    )

    # History is append-only: the database refuses to change or delete it (spine AD-8, AD-20).
    op.execute(
        f"""
        CREATE FUNCTION {SCHEMA}.forbid_history_change() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            RAISE EXCEPTION '% on {SCHEMA}.% is not allowed: history is append-only',
                TG_OP, TG_TABLE_NAME USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$
        """
    )
    for table in HISTORY_TABLES:
        op.execute(
            f"CREATE TRIGGER {table}_append_only BEFORE UPDATE OR DELETE ON {SCHEMA}.{table} "
            f"FOR EACH ROW EXECUTE FUNCTION {SCHEMA}.forbid_history_change()"
        )


def downgrade() -> None:
    for table in HISTORY_TABLES:
        op.execute(f"DROP TRIGGER IF EXISTS {table}_append_only ON {SCHEMA}.{table}")
    op.execute(f"DROP FUNCTION IF EXISTS {SCHEMA}.forbid_history_change()")
    for table in (
        "schedule_overrides",
        "idempotency_keys",
        "audit_events",
        "event_revisions",
        "events",
        "evidence_records",
        "resources",
        "memberships",
        "clubs",
        "users",
    ):
        op.drop_table(table, schema=SCHEMA)
