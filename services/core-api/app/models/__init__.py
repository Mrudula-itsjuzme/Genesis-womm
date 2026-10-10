"""Importing this package registers every Core table on ``Base.metadata`` (used by Alembic)."""

from app.models import directory, scheduling

__all__ = ["directory", "scheduling"]
