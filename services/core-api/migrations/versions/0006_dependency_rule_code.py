"""Name the fixed dependency rule code without implying a UUID identity."""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("event_dependencies", "rule_id", new_column_name="rule_code", schema="core")
    op.execute(
        "ALTER TABLE core.event_dependencies RENAME CONSTRAINT "
        "ck_event_dependencies_rule_id TO ck_event_dependencies_rule_code"
    )


def downgrade() -> None:
    op.execute(
        "ALTER TABLE core.event_dependencies RENAME CONSTRAINT "
        "ck_event_dependencies_rule_code TO ck_event_dependencies_rule_id"
    )
    op.alter_column("event_dependencies", "rule_code", new_column_name="rule_id", schema="core")
