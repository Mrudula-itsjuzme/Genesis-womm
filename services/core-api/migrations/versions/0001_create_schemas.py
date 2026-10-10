"""Create the Core-owned schemas.

Revision ID: 0001
Revises:
Create Date: 2026-10-10
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # `core` is also created by env.py because it holds the version table; both are idempotent.
    op.execute("CREATE SCHEMA IF NOT EXISTS core")
    op.execute("CREATE SCHEMA IF NOT EXISTS student_private")


def downgrade() -> None:
    # `core` is kept: it holds alembic_version_core. No CASCADE, so this fails loudly if any
    # student-private table still exists instead of silently deleting data.
    op.execute("DROP SCHEMA IF EXISTS student_private")
