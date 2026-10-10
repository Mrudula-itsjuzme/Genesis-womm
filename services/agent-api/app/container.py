"""Composition root: the only place that wires adapters to use cases."""

from dataclasses import dataclass

from app.orchestration.readiness import ReadinessService
from app.settings import Settings


@dataclass
class Container:
    readiness: ReadinessService

    async def aclose(self) -> None:
        """Release HTTP clients. None exist yet; the Core and RAG clients arrive with Plan 03."""


def build_container(settings: Settings) -> Container:
    readiness = ReadinessService(
        provider=settings.agent_model_provider,
        has_credential=bool(settings.groq_api_key.get_secret_value()),
    )
    return Container(readiness=readiness)
