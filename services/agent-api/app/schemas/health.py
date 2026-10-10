from typing import Literal

from pydantic import BaseModel, Field


class HealthOut(BaseModel):
    """Process liveness. Says nothing about dependencies."""

    status: Literal["ok"]
    service: str
    version: str


class ReadyOut(BaseModel):
    """The Agent can run a turn: a model provider is configured."""

    status: Literal["ready"]
    checks: dict[str, bool]
    # Core and RAG reachability would appear here as information only; it never gates readiness.
    informational: dict[str, str] = Field(default_factory=dict)
