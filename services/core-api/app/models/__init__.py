"""Importing this package registers every Core table on ``Base.metadata`` (used by Alembic)."""

from app.models import agent, changes, directory, proposal, scheduling

__all__ = ["agent", "changes", "directory", "proposal", "scheduling"]
