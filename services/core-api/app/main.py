"""Application factory. Run with ``uvicorn app.main:create_app --factory``."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.errors import install_error_handlers
from app.api.middleware import RequestIdMiddleware
from app.api.routes import agent, auth, events, health, internal, overrides, proposals, resources
from app.container import Container, build_container
from app.logging import configure_logging
from app.settings import Settings, load_settings

DESCRIPTION = (
    "Operational state, authorization, deterministic scheduling and audit history for CampusCue. "
    "A tentative proposal is not a booking; availability is UNKNOWN until evidence says "
    "otherwise. Routes marked 'Not implemented' return 501 with the standard error envelope."
)


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or load_settings()
    container = container or build_container(settings)
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        container.dispose()

    app = FastAPI(
        title="CampusCue Core API",
        version=__version__,
        description=DESCRIPTION,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.readiness = container.readiness
    app.state.sessions = container.sessions
    app.state.schedule_write = container.schedule_write
    app.state.event_reads = container.event_reads
    app.state.resource_reads = container.resource_reads
    app.state.resource_interests = container.resource_interests
    app.state.conflict_checks = container.conflict_checks
    app.state.delegation = container.delegation
    app.state.agent_actions = container.agent_actions
    app.state.chat = container.chat
    app.state.proposals = container.proposals
    app.state.changes = container.changes
    if container.internal_api_key is not None:
        # Absent means the facade fails closed (api/deps.py), never open.
        app.state.internal_api_key = container.internal_api_key

    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID"],
    )
    install_error_handlers(app)
    app.include_router(health.router)
    for router in (
        auth.router,
        events.router,
        resources.router,
        agent.router,
        internal.router,
        proposals.router,
        overrides.router,
    ):
        app.include_router(router)
    return app
