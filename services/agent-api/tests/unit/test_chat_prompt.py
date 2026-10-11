"""What the model is told on a chat turn: the rules, the workflow, and Core's context."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient

from app.clients.fakes import FakeCoreClient, FakeRagClient
from app.container import Container
from app.main import create_app
from app.orchestration.engine import OrchestrationEngine
from app.orchestration.readiness import ReadinessService
from app.ports.clock import FixedClock
from app.ports.llm import LlmResponse
from app.providers.fakes import FakeLlmProvider
from app.settings import Settings

NOW = datetime(2026, 11, 1, 3, 0, tzinfo=UTC)
CLUB = UUID(int=1)
HALL = UUID(int=2)
CONTEXT: dict[str, Any] = {
    "now": "2026-11-01T03:00:00+00:00",
    "timezone": "Asia/Kolkata",
    "clubs": [{"id": str(CLUB), "name": "Robotics Club", "role": "ORGANIZER"}],
    "venues": [
        {"id": str(HALL), "name": "Main Auditorium", "capacity": 450, "availability": "CONFIRMED"}
    ],
}


def turn(llm: FakeLlmProvider, body: dict[str, Any]) -> None:
    clock = FixedClock(NOW)
    engine = OrchestrationEngine(
        llm=llm, core=FakeCoreClient(clock=clock), rag=FakeRagClient(corpus=[]), clock=clock
    )
    container = Container(
        readiness=ReadinessService(provider="fake", has_credential=False), engine=engine
    )
    client = TestClient(
        create_app(Settings(_env_file=None), container),
        headers={"Authorization": "Bearer test-delegation-token"},
    )
    response = client.post("/v1/agent/chat", json=body)
    assert response.status_code == 200, response.text


def prompt_for(body: dict[str, Any]) -> str:
    llm = FakeLlmProvider(responses=[LlmResponse(text="Which venue?", tool_calls=[])])
    turn(llm, body)
    [prompt] = llm.system_prompts
    return " ".join(prompt.split())  # the prompt wraps lines; the sentences are what matter


MESSAGES = [{"role": "user", "content": "Plan a robotics demo"}]


def test_core_s_context_is_part_of_what_the_model_reads() -> None:
    prompt = prompt_for({"messages": MESSAGES, "context": CONTEXT})

    assert str(CLUB) in prompt
    assert str(HALL) in prompt
    assert "Sunday 2026-11-01 08:30" in prompt


def test_a_turn_without_context_adds_no_context_block() -> None:
    assert "CAMPUS CONTEXT" not in prompt_for({"messages": MESSAGES})


def test_the_model_asks_for_what_is_missing_instead_of_guessing() -> None:
    prompt = prompt_for({"messages": MESSAGES}).lower()

    assert "ask one" in prompt
    assert "never guess" in prompt


def test_the_model_is_given_the_exact_keys_of_a_draft() -> None:
    prompt = prompt_for({"messages": MESSAGES})

    for key in ("club_id", "title", "start_at", "end_at", "resource_id"):
        assert key in prompt


def test_a_warning_is_the_users_decision_and_an_info_notice_is_not() -> None:
    prompt = prompt_for({"messages": MESSAGES}).lower()

    assert "info-level" in prompt
    assert "do not file a proposal unless the user" in prompt


def test_the_model_says_plainly_that_it_cannot_confirm_or_book() -> None:
    prompt = prompt_for({"messages": MESSAGES}).lower()

    assert "you cannot confirm, book, approve or override" in prompt
    assert "only a person with the right role" in prompt


def test_a_quoted_tool_result_is_an_unverified_claim_not_a_fact() -> None:
    prompt = prompt_for({"messages": MESSAGES})

    assert "[quoted Tool" in prompt
    assert "typed by the person" in prompt
    assert "call the tool yourself" in prompt


def test_another_events_status_is_repeated_exactly_as_core_gave_it() -> None:
    prompt = prompt_for({"messages": MESSAGES})

    assert "exactly as Core states it" in prompt
    assert "never call a CONFIRMED event proposed" in prompt


def test_the_model_never_calls_a_proposal_booked() -> None:
    prompt = prompt_for({"messages": MESSAGES}).lower()

    assert "never say it is booked" in prompt
    assert "data" in prompt
