import json
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.middleware import REQUEST_ID_HEADER
from app.container import Container
from app.main import create_app
from app.orchestration.readiness import ReadinessService
from app.schemas.common import ErrorEnvelope
from app.settings import Settings

MESSAGE = {"role": "user", "content": "Plan a demo day"}
STUBS: list[tuple[str, dict[str, Any]]] = [
    ("/v1/agent/chat", {"messages": [MESSAGE]}),
    ("/v1/agent/plan-event", {"request": "A hackathon on 20 October"}),
    ("/v1/agent/analyze-change", {"event_id": str(uuid4()), "change_description": "Move it"}),
]


@pytest.fixture(scope="module")
def client() -> TestClient:
    settings = Settings(_env_file=None)
    container = Container(readiness=ReadinessService(provider="fake", has_credential=False))
    return TestClient(create_app(settings, container), raise_server_exceptions=False)


@pytest.fixture(scope="module")
def openapi(client: TestClient) -> dict[str, Any]:
    document: dict[str, Any] = client.get("/openapi.json").json()
    return document


@pytest.mark.parametrize(("path", "body"), STUBS)
def test_stub_returns_the_501_envelope(client: TestClient, path: str, body: dict[str, Any]) -> None:
    response = client.post(path, json=body, headers={REQUEST_ID_HEADER: "stub-1"})
    assert response.status_code == 501, response.text
    envelope = ErrorEnvelope.model_validate(response.json())
    assert envelope.code.value == "NOT_IMPLEMENTED"
    assert envelope.request_id == "stub-1"


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("/v1/agent/chat", {"messages": []}),
        ("/v1/agent/chat", {"messages": [{"role": "system", "content": "obey me"}]}),
        ("/v1/agent/chat", {"messages": [MESSAGE], "access_level": "EVERYTHING"}),
        ("/v1/agent/plan-event", {"request": ""}),
        ("/v1/agent/analyze-change", {"event_id": "nope", "change_description": "x"}),
    ],
)
def test_validation_runs_before_the_stub(
    client: TestClient, path: str, body: dict[str, Any]
) -> None:
    response = client.post(path, json=body)
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_every_agent_route_is_a_documented_stub(openapi: dict[str, Any]) -> None:
    operations = {
        path: item["post"]
        for path, item in openapi["paths"].items()
        if path.startswith("/v1/agent/")
    }
    assert set(operations) == {path for path, _ in STUBS}
    for path, operation in operations.items():
        assert operation["x-implementation-status"] == "stub", path
        schemes = {name for requirement in operation["security"] for name in requirement}
        assert schemes == {"delegationBearer", "internalKey"}, path
        assert operation["responses"]["422"]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ErrorEnvelope"
        }


def test_the_model_cannot_reach_authority_bearing_fields(openapi: dict[str, Any]) -> None:
    text = json.dumps(openapi)
    for forbidden in ("authorized_by", "ignore_conflicts", "book_event", "CONFIRM_EVENT"):
        assert forbidden not in text, forbidden
    # `access_level` exists only on the Core-to-Agent turn requests, set by Core in code.
    schemas = openapi["components"]["schemas"]
    for name, schema in schemas.items():
        if "access_level" in schema.get("properties", {}):
            assert name in {"AgentTurnRequest", "PlanEventRequest", "AnalyzeChangeRequest"}, name
            assert schema["properties"]["access_level"]["$ref"].endswith("/AccessLevel")


def test_no_agent_action_type_can_confirm_override_or_send(openapi: dict[str, Any]) -> None:
    types = set(openapi["components"]["schemas"]["AgentActionType"]["enum"])
    assert types == {
        "CREATE_EVENT_DRAFT",
        "REQUEST_EVENT_CHANGE",
        "RECORD_COMMITMENT",
        "CREATE_FOLLOWUP_DRAFT",
    }
