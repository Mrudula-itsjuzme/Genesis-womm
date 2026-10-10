"""Composition root: the only place that wires adapters to use cases."""

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

from app.clients.delegation import PyJwtDelegationService
from app.clients.tokens import PyJwtTokenService
from app.domain.scheduling import Policy
from app.domain.time import SystemClock
from app.repositories.health import SqlReadinessProbe
from app.repositories.unit_of_work import SqlUnitOfWork
from app.services.agent_actions import AgentActionService
from app.services.conflict_checks import ConflictCheckService
from app.services.delegation import DelegationService
from app.services.event_reads import EventReadService
from app.services.readiness import ReadinessService
from app.services.resource_reads import ResourceReadService
from app.services.schedule_write import ScheduleWriteService
from app.services.sessions import SessionService
from app.settings import Settings

SERVICE_ROOT = Path(__file__).resolve().parents[1]


class UuidSource:
    def new_id(self) -> UUID:
        return uuid4()


@dataclass
class Container:
    readiness: ReadinessService
    engine: Engine | None = None
    sessions: SessionService | None = None
    schedule_write: ScheduleWriteService | None = None
    event_reads: EventReadService | None = None
    resource_reads: ResourceReadService | None = None
    conflict_checks: ConflictCheckService | None = None
    delegation: DelegationService | None = None
    agent_actions: AgentActionService | None = None
    internal_api_key: str | None = None

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
    schedule_write = ScheduleWriteService(
        lambda: SqlUnitOfWork(database_sessions),
        clock=SystemClock(),
        ids=UuidSource(),
        policy=Policy(campus_gap=timedelta(minutes=settings.campus_gap_minutes)),
    )
    conflict_checks = ConflictCheckService(
        lambda: SqlUnitOfWork(database_sessions),
        clock=SystemClock(),
        policy=Policy(campus_gap=timedelta(minutes=settings.campus_gap_minutes)),
    )
    event_reads = EventReadService(lambda: SqlUnitOfWork(database_sessions))
    resource_reads = ResourceReadService(lambda: SqlUnitOfWork(database_sessions))
    delegation = DelegationService(
        lambda: SqlUnitOfWork(database_sessions),
        PyJwtDelegationService(settings.delegation_signing_key.get_secret_value()),
    )
    agent_actions = AgentActionService(
        lambda: SqlUnitOfWork(database_sessions),
        checks=conflict_checks,
        writes=schedule_write,
        clock=SystemClock(),
        ids=UuidSource(),
    )
    return Container(
        readiness=readiness,
        engine=engine,
        sessions=sessions,
        schedule_write=schedule_write,
        event_reads=event_reads,
        resource_reads=resource_reads,
        conflict_checks=conflict_checks,
        delegation=delegation,
        agent_actions=agent_actions,
        internal_api_key=settings.internal_api_key.get_secret_value(),
    )
