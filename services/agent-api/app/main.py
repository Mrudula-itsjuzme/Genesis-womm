"""Application factory. Run with ``uvicorn app.main:create_app --factory``."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api.errors import install_error_handlers
from app.api.middleware import RequestIdMiddleware
from app.api.routes import agent, health
from app.container import Container, build_container
from app.logging import configure_logging
from app.settings import Settings, load_settings

DESCRIPTION = (
    "Bounded tool-calling orchestration for CampusCue. The model explains deterministic results "
    "from Core and cited evidence from RAG, and files proposals for a human to confirm. It "
    "never owns scheduling, authorization or official status. Routes marked 'Not implemented' "
    "return 501 with the standard error envelope."
)


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or load_settings()
    container = container or build_container(settings)
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        yield
        await container.aclose()

    app = FastAPI(
        title="CampusCue Agent API",
        version=__version__,
        description=DESCRIPTION,
        lifespan=lifespan,
    )
    app.state.settings = settings
    app.state.readiness = container.readiness

    app.add_middleware(RequestIdMiddleware)
    install_error_handlers(app)
    app.include_router(health.router)
    app.include_router(agent.router)
    return app
