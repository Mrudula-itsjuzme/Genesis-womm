"""Who may ask the Agent to think (spine AD-10, AD-19, AD-22).

Every turn costs model usage and acts as a user. So the Agent accepts a turn only from Core
(the internal key) and only with a delegation token to forward. A caller without both must be
turned away before the model or any tool is touched.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.clients.fakes import FakeCoreClient, FakeRagClient
from app.container import Container
from app.main import create_app
from app.orchestration.engine import OrchestrationEngine
from app.orchestration.readiness import ReadinessService
from app.ports.clock import FixedClock
from app.ports.core import CallContext
from app.ports.llm import LlmResponse, ToolCall
from app.providers.fakes import FakeLlmProvider
from app.schemas.core import ConflictCheckOut
from app.settings import Settings

NOW = datetime(2026, 10, 10, 4, 0, tzinfo=UTC)
KEY = "i" * 40
TOKEN = "header.payload.signature"
CHAT = {"messages": [{"role": "user", "content": "Plan a demo day"}]}
PLAN = {"request": "A hackathon on 20 November from 9am to 5pm"}
ANALYZE = {"event_id": str(uuid4()), "change_description": "Move it a week later"}
ROUTES = [
    ("/v1/agent/chat", CHAT),
    ("/v1/agent/plan-event", PLAN),
    ("/v1/agent/analyze-change", ANALYZE),
]


class SpyCore(FakeCoreClient):
    """Records the context of every call Core would have received."""

    def __init__(self) -> None:
        super().__init__(clock=FixedClock(NOW))
        self.contexts: list[CallContext] = []

    async def get_event_details(self, event_id: UUID, ctx: CallContext) -> Any:
        self.contexts.append(ctx)
        return await super().get_event_details(event_id, ctx)

    async def check_event_conflicts(self, request: Any, ctx: CallContext) -> ConflictCheckOut:
        self.contexts.append(ctx)
        return await super().check_event_conflicts(request, ctx)


@dataclass
class Rig:
    client: TestClient
    app: FastAPI
    llm: FakeLlmProvider
    core: SpyCore

    def post(self, path: str, body: dict[str, Any], **kwargs: Any) -> Any:
        return self.client.post(path, json=body, **kwargs)


def build(internal_key: str | None = KEY) -> Rig:
    values: dict[str, Any] = {}
    if internal_key is not None:
        values["internal_api_key"] = SecretStr(internal_key)
    settings = Settings(_env_file=None, **values)
    clock = FixedClock(NOW)
    core, llm = SpyCore(), FakeLlmProvider()
    engine = OrchestrationEngine(
        llm=llm,
        core=core,
        rag=FakeRagClient(corpus=[]),
        clock=clock,
        max_tool_calls=6,
        tool_timeout_s=5.0,
        max_tool_bytes=16_384,
    )
    container = Container(
        readiness=ReadinessService(provider="fake", has_credential=False), engine=engine
    )
    app = create_app(settings, container)
    return Rig(TestClient(app, raise_server_exceptions=False), app, llm, core)


def credentials(key: str | None = KEY, token: str | None = TOKEN) -> dict[str, str]:
    sent: dict[str, str] = {}
    if key is not None:
        sent["X-Internal-Key"] = key
    if token is not None:
        sent["Authorization"] = f"Bearer {token}"
    return sent


def model_asks_for_the_event() -> LlmResponse:
    """A scripted model reply that makes the engine call Core, so the token is observable."""
    call = ToolCall(id="1", name="get_event_details", arguments={"event_id": str(uuid4())})
    return LlmResponse(text=None, tool_calls=[call])


@pytest.mark.parametrize(("path", "body"), ROUTES)
def test_a_turn_with_both_credentials_is_answered(path: str, body: dict[str, Any]) -> None:
    response = build().post(path, body, headers=credentials())

    assert response.status_code == 200, response.text


@pytest.mark.parametrize(("path", "body"), ROUTES)
@pytest.mark.parametrize("key", [None, "", "wrong", "i" * 39, "i" * 41, KEY + " "])
def test_a_missing_or_wrong_internal_key_never_reaches_the_model(
    path: str, body: dict[str, Any], key: str | None
) -> None:
    rig = build()

    response = rig.post(path, body, headers=credentials(key=key))

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"
    assert rig.llm.calls == [], "an unauthenticated turn must cost nothing"
    assert rig.core.contexts == []


@pytest.mark.parametrize(("path", "body"), ROUTES)
@pytest.mark.parametrize("token", [None, "", "   ", "\t"])
def test_a_turn_without_a_delegation_token_never_reaches_the_model(
    path: str, body: dict[str, Any], token: str | None
) -> None:
    rig = build()

    response = rig.post(path, body, headers=credentials(token=token))

    assert response.status_code == 401
    assert response.json()["code"] == "UNAUTHENTICATED"
    assert rig.llm.calls == []
    assert rig.core.contexts == []


def test_the_failure_does_not_say_which_credential_was_wrong() -> None:
    rig = build()
    bad_key = rig.post("/v1/agent/chat", CHAT, headers=credentials(key="nope")).json()
    no_token = rig.post("/v1/agent/chat", CHAT, headers=credentials(token=None)).json()

    assert bad_key["message"] == no_token["message"]


def test_the_credentials_are_checked_before_the_body() -> None:
    """A caller without the key learns nothing about the request schema."""
    response = build().post("/v1/agent/chat", {"messages": []}, headers=credentials(key="wrong"))

    assert response.status_code == 401


def test_a_non_ascii_key_is_refused_not_a_server_error() -> None:
    response = build().post(
        "/v1/agent/chat",
        CHAT,
        headers={
            b"X-Internal-Key": "café".encode("latin-1"),
            b"Authorization": f"Bearer {TOKEN}".encode(),
        },
    )

    assert response.status_code == 401


def test_with_no_key_configured_only_the_delegation_is_required() -> None:
    """Local development: settings allow an empty key only when APP_ENV is local."""
    rig = build(internal_key=None)

    with_token = rig.post("/v1/agent/chat", CHAT, headers=credentials(key=None))
    without = rig.post("/v1/agent/chat", CHAT, headers=credentials(key=None, token=None))

    assert (with_token.status_code, without.status_code) == (200, 401)


def test_the_health_endpoints_stay_open() -> None:
    client = build().client

    assert client.get("/health").status_code == 200
    assert client.get("/ready").status_code == 200


def test_a_deployment_with_no_key_published_fails_closed_instead_of_open() -> None:
    rig = build()
    del rig.app.state.internal_api_key

    response = rig.post("/v1/agent/chat", CHAT, headers=credentials())

    assert response.status_code == 500


def test_the_delegation_token_reaches_core_exactly_as_received() -> None:
    rig = build()
    rig.llm.responses = [
        model_asks_for_the_event(),
        LlmResponse(text="Here is the event.", tool_calls=[]),
    ]

    rig.post("/v1/agent/chat", CHAT, headers=credentials(token="a.b.c-exact"))

    assert [c.delegation_token for c in rig.core.contexts] == ["a.b.c-exact"]
