"""Core's HTTP client for the Agent (spine AD-3, AD-10, AD-19).

Every request is recorded and checked against the Agent's published OpenAPI, so a path the
contract does not declare fails here and not as a 404 in production.
"""

import json
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
import respx
import yaml

from app.clients.agent_gateway import HttpAgentGateway
from app.domain.enums import AvailabilityState, Role
from app.services.errors import AgentOutputInvalidError, AgentUnavailableError
from app.services.ports import ChatClub, ChatContext, ChatTurn, ChatVenue
from scripts import export_contracts as export

BASE = "http://agent.test"
URL = f"{BASE}/v1/agent/chat"
TOKEN = "header.payload.signature"
INTERNAL_KEY = "i" * 40
TURN = ChatTurn(messages=(("user", "Plan a demo day"), ("assistant", "For when?")), event_id=None)
REPLY = {"message": "Here is a plan.", "request_id": "req-1", "trace": [], "citations": []}
AGENT_OPENAPI = yaml.safe_load((export.CONTRACTS / "agent-api.openapi.yaml").read_text())


@pytest.fixture
def gateway() -> Iterator[HttpAgentGateway]:
    with httpx.Client(base_url=BASE, headers={"X-Internal-Key": INTERNAL_KEY}) as client:
        yield HttpAgentGateway(client)


def chat(gateway: HttpAgentGateway, turn: ChatTurn = TURN) -> dict[str, Any]:
    return gateway.chat(turn, delegation_token=TOKEN, request_id="req-1")


def declared(method: str, path: str) -> bool:
    for template, operations in AGENT_OPENAPI["paths"].items():
        pattern = "^" + re.sub(r"\{[^}]+\}", "[^/]+", template) + "$"
        if re.match(pattern, path) and method.lower() in operations:
            return True
    return False


# ---- what goes on the wire -------------------------------------------------------------


@respx.mock
def test_the_request_goes_to_a_route_the_agent_publishes(gateway: HttpAgentGateway) -> None:
    respx.post(URL).respond(json=REPLY)

    chat(gateway)

    sent = respx.calls.last.request
    assert declared(sent.method, sent.url.path), f"{sent.method} {sent.url.path} is not published"


@respx.mock
def test_the_credentials_and_request_id_are_sent_as_headers(gateway: HttpAgentGateway) -> None:
    respx.post(URL).respond(json=REPLY)

    chat(gateway)

    headers = respx.calls.last.request.headers
    assert headers["authorization"] == f"Bearer {TOKEN}"
    assert headers["x-internal-key"] == INTERNAL_KEY
    assert headers["x-request-id"] == "req-1"


@respx.mock
def test_the_body_carries_the_turn_and_a_fixed_access_level(gateway: HttpAgentGateway) -> None:
    respx.post(URL).respond(json=REPLY)

    chat(gateway)

    assert json.loads(respx.calls.last.request.content) == {
        "messages": [
            {"role": "user", "content": "Plan a demo day"},
            {"role": "assistant", "content": "For when?"},
        ],
        "access_level": "CAMPUS_PUBLIC",
    }


@respx.mock
def test_the_context_goes_over_in_a_documented_shape(gateway: HttpAgentGateway) -> None:
    club, venue = UUID(int=5), UUID(int=6)
    context = ChatContext(
        now=datetime(2026, 11, 1, 3, 0, tzinfo=UTC),
        clubs=(ChatClub(club, "Robotics Club", Role.ORGANIZER),),
        venues=(ChatVenue(venue, "Main Auditorium", 450, AvailabilityState.CONFIRMED),),
    )
    respx.post(URL).respond(json=REPLY)

    chat(gateway, ChatTurn(messages=(("user", "Plan it"),), context=context))

    sent = json.loads(respx.calls.last.request.content)["context"]
    schemas = AGENT_OPENAPI["components"]["schemas"]
    assert set(sent) == set(schemas["TurnContext"]["properties"])
    assert set(sent["clubs"][0]) == set(schemas["ClubContext"]["properties"])
    assert set(sent["venues"][0]) == set(schemas["VenueContext"]["properties"])
    assert sent == {
        "now": "2026-11-01T03:00:00+00:00",
        "timezone": "Asia/Kolkata",
        "clubs": [{"id": str(club), "name": "Robotics Club", "role": "ORGANIZER"}],
        "venues": [
            {
                "id": str(venue),
                "name": "Main Auditorium",
                "capacity": 450,
                "availability": "CONFIRMED",
            }
        ],
    }


@respx.mock
def test_an_event_the_conversation_is_about_is_named(gateway: HttpAgentGateway) -> None:
    event = uuid4()
    respx.post(URL).respond(json=REPLY)

    chat(gateway, ChatTurn(messages=(("user", "Move it"),), event_id=event))

    assert json.loads(respx.calls.last.request.content)["event_id"] == str(event)


@respx.mock
def test_the_reply_is_returned_as_the_agent_sent_it(gateway: HttpAgentGateway) -> None:
    respx.post(URL).respond(json={**REPLY, "proposed_actions": [{"action_id": "x"}]})

    assert chat(gateway) == {**REPLY, "proposed_actions": [{"action_id": "x"}]}


# ---- failures --------------------------------------------------------------------------


@pytest.mark.parametrize("status", [401, 403, 500, 502, 503, 504])
@respx.mock
def test_a_failing_or_unauthorized_agent_is_unavailable(
    gateway: HttpAgentGateway, status: int
) -> None:
    respx.post(URL).respond(status, json={"code": "INTERNAL_ERROR"})

    with pytest.raises(AgentUnavailableError):
        chat(gateway)


@pytest.mark.parametrize("status", [400, 404, 409, 422])
@respx.mock
def test_an_agent_that_rejects_the_turn_gave_an_unusable_answer(
    gateway: HttpAgentGateway, status: int
) -> None:
    respx.post(URL).respond(status, json={"code": "VALIDATION_ERROR"})

    with pytest.raises(AgentOutputInvalidError):
        chat(gateway)


@pytest.mark.parametrize(
    "error",
    [
        httpx.ConnectError("refused"),
        httpx.ConnectTimeout("slow"),
        httpx.ReadTimeout("silent"),
        httpx.RemoteProtocolError("hung up"),
    ],
    ids=lambda e: type(e).__name__,
)
@respx.mock
def test_network_failures_are_unavailable(gateway: HttpAgentGateway, error: Exception) -> None:
    respx.post(URL).mock(side_effect=error)

    with pytest.raises(AgentUnavailableError):
        chat(gateway)


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, text="not json at all"),
        httpx.Response(200, json=["a", "list"]),
        httpx.Response(200, json="a string"),
        httpx.Response(200, content=b""),
    ],
    ids=["not json", "a list", "a string", "empty body"],
)
@respx.mock
def test_a_success_that_is_not_a_json_object_is_unusable(
    gateway: HttpAgentGateway, response: httpx.Response
) -> None:
    respx.post(URL).mock(return_value=response)

    with pytest.raises(AgentOutputInvalidError):
        chat(gateway)


@respx.mock
def test_no_error_message_carries_the_token_the_key_or_the_agents_words(
    gateway: HttpAgentGateway,
) -> None:
    respx.post(URL).respond(500, text=f"boom {TOKEN} {INTERNAL_KEY} secret-reply")

    with pytest.raises(AgentUnavailableError) as failed:
        chat(gateway)

    for secret in (TOKEN, INTERNAL_KEY, "secret-reply"):
        assert secret not in str(failed.value)


@respx.mock
def test_a_network_error_message_is_not_passed_on(gateway: HttpAgentGateway) -> None:
    respx.post(URL).mock(
        side_effect=httpx.ConnectError(f"cannot reach http://agent-internal:8001 for {TOKEN}")
    )

    with pytest.raises(AgentUnavailableError) as failed:
        chat(gateway)

    assert "agent-internal" not in str(failed.value)
    assert TOKEN not in str(failed.value)
    assert "ConnectError" in str(failed.value)
