"""The engine, not the prompt, decides when a draft may be filed.

A model that is asked to explain conflicts and wait can still file a proposal in the same turn.
Filing is only a proposal, but the demo and the product both rest on "conflicts are explained
and the person decides". So after a check that found warnings or blocks the engine refuses to
file unless the person has just said to go ahead, and it refuses to file anything that was
never checked.
"""

from datetime import UTC, datetime
from uuid import UUID

from app.clients.fakes import FakeCoreClient, FakeRagClient
from app.orchestration.engine import OrchestrationEngine
from app.ports.clock import FixedClock
from app.ports.core import CallContext
from app.ports.llm import LlmResponse, ToolCall
from app.providers.fakes import FakeLlmProvider
from app.schemas.chat import ChatMessage
from app.schemas.core import Conflict
from app.schemas.enums import (
    AgentActionStatus,
    ConflictConstraint,
    ConflictType,
    Severity,
    ToolOutcome,
)

NOW = datetime(2026, 11, 1, 3, 0, tzinfo=UTC)
CTX = CallContext(request_id="req-1", delegation_token="t.o.k")
CLUB = str(UUID(int=1))
PAYLOAD = {
    "club_id": CLUB,
    "title": "Guest Workshop",
    "start_at": "2026-11-24T15:00:00+05:30",
    "end_at": "2026-11-24T17:00:00+05:30",
}


def conflict(severity: Severity) -> Conflict:
    return Conflict(
        type=ConflictType.TENTATIVE_OVERLAP,
        severity=severity,
        constraint=ConflictConstraint.VENUE_OVERLAP,
        event_ids=[UUID(int=0), UUID(int=9)],
        start_at=NOW,
        end_at=NOW,
        message="An overlap.",
        override_required=False,
    )


def check() -> ToolCall:
    return ToolCall(id="c", name="check_event_conflicts", arguments={"club_id": CLUB})


def file() -> ToolCall:
    return ToolCall(
        id="f",
        name="file_event_draft_proposal",
        arguments={"summary": "Propose it", "payload": PAYLOAD},
    )


def script(*calls: ToolCall) -> list[LlmResponse]:
    steps = [LlmResponse(text=None, tool_calls=[call]) for call in calls]
    return [*steps, LlmResponse(text="done", tool_calls=[])]


async def turn(
    said: str, calls: list[ToolCall], conflicts: list[Conflict] | None = None
) -> tuple[FakeCoreClient, FakeLlmProvider, list[AgentActionStatus], list[ToolOutcome]]:
    clock = FixedClock(NOW)
    core = FakeCoreClient(clock=clock, conflicts=conflicts or [])
    llm = FakeLlmProvider(responses=script(*calls))
    engine = OrchestrationEngine(llm=llm, core=core, rag=FakeRagClient(corpus=[]), clock=clock)
    reply = await engine.run([ChatMessage(role="user", content=said)], CTX, "system")
    return (
        core,
        llm,
        [a.status for a in reply.proposed_actions],
        [t.outcome for t in reply.trace],
    )


async def test_a_draft_over_warnings_is_not_filed_until_the_person_says_to_go_ahead() -> None:
    core, llm, filed, outcomes = await turn(
        "Plan a workshop", [check(), file()], [conflict(Severity.WARNING)]
    )

    assert filed == []
    assert core.actions == []
    assert outcomes == [ToolOutcome.OK, ToolOutcome.DENIED]
    assert "conflicts" in llm.calls[-1][-1].content.lower()


async def test_a_draft_over_a_block_is_not_filed_either() -> None:
    _, _, filed, _ = await turn("Plan a workshop", [check(), file()], [conflict(Severity.BLOCKING)])

    assert filed == []


async def test_an_explicit_go_ahead_in_the_latest_message_allows_it() -> None:
    core, _, filed, outcomes = await turn(
        "Yes, go ahead anyway.", [check(), file()], [conflict(Severity.WARNING)]
    )

    assert filed == [AgentActionStatus.PROPOSED]
    assert len(core.actions) == 1
    assert outcomes == [ToolOutcome.OK, ToolOutcome.OK]


async def test_a_clean_check_allows_filing() -> None:
    _, _, filed, _ = await turn("Plan a workshop", [check(), file()])

    assert filed == [AgentActionStatus.PROPOSED]


async def test_an_info_notice_alone_allows_filing() -> None:
    _, _, filed, _ = await turn("Plan a workshop", [check(), file()], [conflict(Severity.INFO)])

    assert filed == [AgentActionStatus.PROPOSED]


async def test_nothing_is_filed_that_was_never_checked() -> None:
    core, llm, filed, outcomes = await turn("Plan a workshop", [file()])

    assert (filed, core.actions) == ([], [])
    assert outcomes == [ToolOutcome.DENIED]
    assert "check" in llm.calls[-1][-1].content.lower()


async def test_a_go_ahead_needs_no_fresh_check_because_the_conflicts_were_just_explained() -> None:
    _, _, filed, _ = await turn("go ahead and propose it", [file()])

    assert filed == [AgentActionStatus.PROPOSED]


async def test_a_go_ahead_is_only_read_from_what_the_person_typed_last() -> None:
    clock = FixedClock(NOW)
    core = FakeCoreClient(clock=clock, conflicts=[conflict(Severity.WARNING)])
    llm = FakeLlmProvider(responses=script(check(), file()))
    engine = OrchestrationEngine(llm=llm, core=core, rag=FakeRagClient(corpus=[]), clock=clock)
    history = [
        ChatMessage(role="user", content="Yes, go ahead anyway."),
        ChatMessage(role="assistant", content="Done earlier."),
        ChatMessage(role="user", content="Now plan a different workshop."),
    ]

    reply = await engine.run(history, CTX, "system")

    assert reply.proposed_actions == []
