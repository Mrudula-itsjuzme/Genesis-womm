"""Composition root: the only place that wires adapters to use cases."""

from dataclasses import dataclass
from datetime import UTC, datetime

import httpx

from app.clients.core_api import HttpCoreClient
from app.clients.rag_api import HttpRagClient
from app.orchestration.engine import OrchestrationEngine
from app.orchestration.readiness import ReadinessService
from app.ports.clock import FixedClock
from app.providers.fakes import FakeLlmProvider
from app.providers.groq import GroqProvider
from app.providers.llm import LlmPort
from app.settings import Settings


@dataclass
class Container:
    readiness: ReadinessService
    engine: OrchestrationEngine | None = None
    _core_http: httpx.AsyncClient | None = None
    _rag_http: httpx.AsyncClient | None = None

    async def aclose(self) -> None:
        if self._core_http:
            await self._core_http.aclose()
        if self._rag_http:
            await self._rag_http.aclose()


def build_container(settings: Settings) -> Container:
    readiness = ReadinessService(
        provider=settings.agent_model_provider,
        has_credential=bool(settings.groq_api_key.get_secret_value()),
    )

    # LLM provider
    llm: LlmPort
    if settings.agent_model_provider == "groq":
        llm = GroqProvider(
            api_key=settings.groq_api_key.get_secret_value(),
            model=settings.groq_model,
        )
    else:
        llm = FakeLlmProvider()

    # HTTP clients
    core_http = httpx.AsyncClient(
        base_url=settings.core_api_url,
        timeout=settings.tool_timeout_s,
        headers={"X-Internal-Key": settings.internal_api_key.get_secret_value()},
    )
    rag_http = httpx.AsyncClient(
        base_url=settings.rag_api_url,
        timeout=settings.tool_timeout_s,
    )

    core_client = HttpCoreClient(core_http)
    rag_client = HttpRagClient(rag_http)
    clock = FixedClock(datetime.now(UTC))

    engine = OrchestrationEngine(
        llm=llm,
        core=core_client,
        rag=rag_client,
        clock=clock,
        max_tool_calls=settings.max_tool_calls,
        tool_timeout_s=settings.tool_timeout_s,
        max_tool_bytes=settings.max_tool_bytes,
    )

    container = Container(readiness=readiness, engine=engine)
    container._core_http = core_http
    container._rag_http = rag_http
    return container
