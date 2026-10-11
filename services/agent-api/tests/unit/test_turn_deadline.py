"""A turn that outlives its deadline is stopped by the Agent, before Core gives up on it."""

import asyncio
from datetime import UTC, datetime

import pytest

from app.clients.fakes import FakeCoreClient, FakeRagClient
from app.orchestration.engine import OrchestrationEngine
from app.ports.clock import FixedClock
from app.ports.core import CallContext
from app.ports.errors import DependencyUnavailableError
from app.ports.llm import LlmResponse
from app.schemas.chat import ChatMessage

CTX = CallContext(request_id="req-1", delegation_token="t.o.k")
USER = [ChatMessage(role="user", content="hello")]


class SlowLlm:
    def __init__(self, delay: float) -> None:
        self.delay = delay

    async def complete(self, *_: object) -> LlmResponse:
        await asyncio.sleep(self.delay)
        return LlmResponse(text="late", tool_calls=[])


def engine(delay: float, deadline: float) -> OrchestrationEngine:
    clock = FixedClock(datetime(2026, 11, 1, tzinfo=UTC))
    return OrchestrationEngine(
        llm=SlowLlm(delay),
        core=FakeCoreClient(clock=clock),
        rag=FakeRagClient(corpus=[]),
        clock=clock,
        turn_deadline_s=deadline,
    )


async def test_a_turn_that_takes_too_long_is_a_dependency_failure() -> None:
    with pytest.raises(DependencyUnavailableError):
        await engine(delay=1.0, deadline=0.05).run(USER, CTX, "system")


async def test_a_turn_inside_its_deadline_completes() -> None:
    reply = await engine(delay=0.0, deadline=1.0).run(USER, CTX, "system")

    assert reply.message == "late"
