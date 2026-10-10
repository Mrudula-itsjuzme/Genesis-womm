"""Readiness: can the Agent run a turn? (spine AD-19)

The Agent is ready when a model provider is configured. The `fake` provider is always
configured. Core and RAG reachability are information only and never gate readiness.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ReadinessReport:
    ready: bool
    checks: dict[str, bool]
    provider: str


class ReadinessService:
    def __init__(self, provider: str, has_credential: bool) -> None:
        self._provider = provider
        self._has_credential = has_credential

    def check(self) -> ReadinessReport:
        configured = self._provider == "fake" or (self._provider == "groq" and self._has_credential)
        return ReadinessReport(
            ready=configured,
            checks={"model_provider": configured},
            provider=self._provider,
        )
