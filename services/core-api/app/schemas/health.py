from typing import Literal

from pydantic import BaseModel, Field


class HealthOut(BaseModel):
    """Process liveness. Says nothing about dependencies."""

    status: Literal["ok"]
    service: str
    version: str


class ReadyOut(BaseModel):
    """Core can do its own job: database reachable and migration head applied."""

    status: Literal["ready"]
    checks: dict[str, bool]
    migration_head: str | None
    expected_head: str
    # Agent, RAG and LLM state belongs here as information only; it never affects readiness.
    informational: dict[str, str] = Field(default_factory=dict)
