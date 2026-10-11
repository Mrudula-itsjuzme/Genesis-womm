"""The chat window shows plain text, so Markdown a model writes anyway is cleaned up in code.

Telling the model not to is not enough: it complies most of the time, and the other times the
audience reads `**PROPOSED**` with its asterisks. Only presentation marks are removed; the words,
numbers and line structure stay exactly as written.
"""

import pytest

from app.orchestration.plain import plain_text


@pytest.mark.parametrize(
    ("written", "shown"),
    [
        ("The proposal is **PROPOSED** now.", "The proposal is PROPOSED now."),
        ("It is __bold__ too.", "It is bold too."),
        ("Run `check_event_conflicts` first.", "Run check_event_conflicts first."),
        ("## Conflicts found", "Conflicts found"),
        ("### Next steps\n- one", "Next steps\n- one"),
        ("* first\n* second", "- first\n- second"),
        ("  * indented bullet", "  - indented bullet"),
    ],
)
def test_presentation_marks_are_removed(written: str, shown: str) -> None:
    assert plain_text(written) == shown


@pytest.mark.parametrize(
    "text",
    [
        "Plain words, 120 minutes, 20 Nov 2026 10:00-12:00 IST.",
        "- already a plain bullet\n- another",
        "2 * 3 = 6 and a * b are arithmetic, not emphasis.",
        "A snake_case_name and file__name stay intact.",
        "Price Rs. 1,45,000 (about 6.5 percent) #1 priority",
        "Line one\n\nLine three after a blank line",
        "a__b__c inside a word is not emphasis",
        "Use the # symbol here, or ## in the middle of a sentence",
        "",
    ],
)
def test_ordinary_text_is_left_exactly_as_it_is(text: str) -> None:
    assert plain_text(text) == text


def test_an_unbalanced_marker_is_not_guessed_at() -> None:
    assert plain_text("Half **open emphasis and more") == "Half **open emphasis and more"


def test_emphasis_is_never_stitched_across_lines() -> None:
    text = "**one line\nand the next**"

    assert plain_text(text) == text


def test_line_breaks_survive() -> None:
    assert plain_text("**A**\n**B**\n\n**C**") == "A\nB\n\nC"


# ---- through the engine ----------------------------------------------------------------


async def test_the_reply_the_person_reads_has_no_markdown() -> None:
    from datetime import UTC, datetime

    from app.clients.fakes import FakeCoreClient, FakeRagClient
    from app.orchestration.engine import OrchestrationEngine
    from app.ports.clock import FixedClock
    from app.ports.core import CallContext
    from app.ports.llm import LlmResponse
    from app.providers.fakes import FakeLlmProvider
    from app.schemas.chat import ChatMessage

    clock = FixedClock(datetime(2026, 11, 1, tzinfo=UTC))
    llm = FakeLlmProvider(
        responses=[LlmResponse(text="The draft is **PROPOSED**.\n* one", tool_calls=[])]
    )
    engine = OrchestrationEngine(
        llm=llm, core=FakeCoreClient(clock=clock), rag=FakeRagClient(corpus=[]), clock=clock
    )

    reply = await engine.run(
        [ChatMessage(role="user", content="hi")],
        CallContext(request_id="r", delegation_token="t.o.k"),
        "system",
    )

    assert reply.message == "The draft is PROPOSED.\n- one"
