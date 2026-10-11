"""Composition root: the only place that wires adapters to use cases."""

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

from app.clients.agent_gateway import HttpAgentGateway
from app.clients.delegation import PyJwtDelegationService
from app.clients.rag_ingest import HttpRagIngest
from app.clients.tokens import PyJwtTokenService
from app.domain.scheduling import Policy
from app.domain.time import SystemClock
from app.repositories.health import SqlReadinessProbe
from app.repositories.unit_of_work import SqlUnitOfWork
from app.services.agent_actions import AgentActionService
from app.services.change_queries import ChangeQueries
from app.services.chat import ChatService
from app.services.chat_context import ChatContextBuilder
from app.services.conflict_checks import ConflictCheckService
from app.services.delegation import DelegationService
from app.services.event_reads import EventReadService
from app.services.minio_client import MinIOProposalStorage
from app.services.proposal_lifecycle import ProposalLifecycleManager
from app.services.proposals import ProposalService
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
    chat: ChatService | None = None
    proposals: ProposalService | None = None
    changes: ChangeQueries | None = None
    agent_client: httpx.Client | None = None
    rag_client: httpx.Client | None = None
    internal_api_key: str | None = None

    def dispose(self) -> None:
        for client in (self.agent_client, self.rag_client):
            if client is not None:
                client.close()
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
    agent_client = httpx.Client(
        base_url=settings.agent_api_url,
        timeout=settings.agent_client_timeout_s,
        headers={"X-Internal-Key": settings.internal_api_key.get_secret_value()},
    )
    chat = ChatService(
        delegation=delegation,
        gateway=HttpAgentGateway(agent_client),
        actions=agent_actions,
        context=ChatContextBuilder(lambda: SqlUnitOfWork(database_sessions), clock=SystemClock()),
    )

    def proposal_storage(public_endpoint: str | None = None) -> MinIOProposalStorage:
        return MinIOProposalStorage(
            endpoint=settings.minio_endpoint,
            public_endpoint=public_endpoint,
            access_key=settings.minio_access_key.get_secret_value(),
            secret_key=settings.minio_secret_key.get_secret_value(),
            proposal_bucket=settings.minio_proposal_bucket,
            archive_bucket=settings.minio_archive_bucket,
            use_ssl=settings.minio_use_ssl,
        )

    storage = proposal_storage(settings.minio_public_endpoint)
    proposal_clock = SystemClock()
    rag_client = httpx.Client(base_url=settings.rag_api_url, timeout=10.0)
    proposals = ProposalService(
        lambda: SqlUnitOfWork(database_sessions),
        storage=storage,
        manager=ProposalLifecycleManager(
            proposal_storage(),
            HttpRagIngest(rag_client),
            proposal_clock,
        ),
        clock=proposal_clock,
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
        chat=chat,
        proposals=proposals,
        changes=ChangeQueries(
            lambda: SqlUnitOfWork(database_sessions),
            policy=Policy(campus_gap=timedelta(minutes=settings.campus_gap_minutes)),
        ),
        agent_client=agent_client,
        rag_client=rag_client,
        internal_api_key=settings.internal_api_key.get_secret_value(),
    )
