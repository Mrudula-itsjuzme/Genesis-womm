"""Composition root: the only place that wires adapters to use cases."""

from dataclasses import dataclass
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

from app.clients.tokens import PyJwtTokenService
from app.repositories.health import SqlReadinessProbe
from app.repositories.unit_of_work import SqlUnitOfWork
from app.services.readiness import ReadinessService
from app.services.sessions import SessionService
from app.settings import Settings

SERVICE_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Container:
    readiness: ReadinessService
    engine: Engine | None = None
    sessions: SessionService | None = None

    def dispose(self) -> None:
        if self.engine is not None:
            self.engine.dispose()


def expected_migration_head() -> str:
    script = ScriptDirectory.from_config(Config(str(SERVICE_ROOT / "alembic.ini")))
    head = script.get_current_head()
    if head is None:
        raise RuntimeError("no Alembic migrations found")
    return head


def build_container(settings: Settings) -> Container:
    # create_engine does not connect, so the API starts even when the database is down
    # and /ready reports it instead.
    engine = create_engine(
        settings.database_url,
        pool_pre_ping=True,
        connect_args={"connect_timeout": 3},
    )
    readiness = ReadinessService(SqlReadinessProbe(engine), expected_migration_head())
    database_sessions = sessionmaker(bind=engine, expire_on_commit=False)
    sessions = SessionService(
        lambda: SqlUnitOfWork(database_sessions),
        PyJwtTokenService(settings.session_signing_key.get_secret_value()),
    )
    return Container(readiness=readiness, engine=engine, sessions=sessions)
