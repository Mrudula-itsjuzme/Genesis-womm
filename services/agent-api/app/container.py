"""Composition root: the only place that wires adapters to use cases."""

from dataclasses import dataclass

import httpx

from app.clients.core_api import HttpCoreClient
from app.clients.rag_api import HttpRagClient
from app.clients.system import SystemClock
from app.orchestration.engine import OrchestrationEngine
from app.orchestration.readiness import ReadinessService
from app.ports.llm import LlmPort
from app.providers.fakes import FakeLlmProvider
from app.providers.groq import GroqProvider
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
            fallback_model=settings.groq_fallback_model,
            timeout_s=settings.groq_timeout_s,
        )
    else:
        llm = FakeLlmProvider(demo_mode=settings.agent_demo_mode)

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

    engine = OrchestrationEngine(
        llm=llm,
        core=core_client,
        rag=rag_client,
        clock=SystemClock(),
        max_tool_calls=settings.max_tool_calls,
        tool_timeout_s=settings.tool_timeout_s,
        max_tool_bytes=settings.max_tool_bytes,
        turn_deadline_s=settings.turn_deadline_s,
    )

    container = Container(readiness=readiness, engine=engine)
    container._core_http = core_http
    container._rag_http = rag_http
    return container
