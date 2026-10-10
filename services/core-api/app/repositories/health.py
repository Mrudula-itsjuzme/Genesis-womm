"""Database-backed readiness probe (implements ``services.readiness.ReadinessProbe``)."""

import structlog
from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.models.base import CORE_SCHEMA, VERSION_TABLE

log = structlog.get_logger("readiness")


class SqlReadinessProbe:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def database_reachable(self) -> bool:
        try:
            with self._engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError:
            log.warning("database_unreachable")
            return False
        return True

    def applied_migration(self) -> str | None:
        """The applied revision, or None when the version table is missing or empty."""
        query = text(f'SELECT version_num FROM "{CORE_SCHEMA}"."{VERSION_TABLE}"')  # noqa: S608
        try:
            with self._engine.connect() as connection:
                return connection.execute(query).scalar_one_or_none()
        except SQLAlchemyError:
            return None
