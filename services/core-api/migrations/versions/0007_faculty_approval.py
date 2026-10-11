"""Add an explicit faculty-approved document review stage.

Revision ID: 0007
Revises: 0006
"""
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.drop_constraint("ck_proposals_status", "proposals", schema="core", type_="check")
    op.create_check_constraint(
        "ck_proposals_status", "proposals",
        "status IN ('DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'FACULTY_APPROVED', "
        "'APPROVED', 'REJECTED', 'REVISION_REQUESTED', 'CHUNKED', 'ARCHIVED')",
        schema="core",
    )
    op.drop_constraint("ck_proposals_decided_has_reviewer", "proposals", schema="core", type_="check")
    op.create_check_constraint(
        "ck_proposals_decided_has_reviewer", "proposals",
        "status NOT IN ('FACULTY_APPROVED', 'APPROVED', 'REJECTED', 'REVISION_REQUESTED', 'CHUNKED') "
        "OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
        schema="core",
    )

def downgrade() -> None:
    op.execute("UPDATE core.proposals SET status = 'UNDER_REVIEW' WHERE status = 'FACULTY_APPROVED'")
    op.drop_constraint("ck_proposals_decided_has_reviewer", "proposals", schema="core", type_="check")
    op.create_check_constraint(
        "ck_proposals_decided_has_reviewer", "proposals",
        "status NOT IN ('APPROVED', 'REJECTED', 'REVISION_REQUESTED', 'CHUNKED') "
        "OR (reviewed_by IS NOT NULL AND reviewed_at IS NOT NULL)",
        schema="core",
    )
    op.drop_constraint("ck_proposals_status", "proposals", schema="core", type_="check")
    op.create_check_constraint(
        "ck_proposals_status", "proposals",
        "status IN ('DRAFT', 'SUBMITTED', 'UNDER_REVIEW', 'APPROVED', "
        "'REJECTED', 'REVISION_REQUESTED', 'CHUNKED', 'ARCHIVED')",
        schema="core",
    )
