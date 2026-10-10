"""The Agent's HTTP client for Core, against Core's published contract (spine AD-10, AD-18).

Every request the client sends is recorded and checked against `core-api.openapi.yaml`, so a path
the contract does not declare fails here instead of as a 404 in production.
"""

import json
import re
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
import respx
import yaml

from app.clients.core_api import HttpCoreClient
from app.ports.core import CallContext
from app.ports.errors import (
    ContractViolationError,
    DeniedError,
    DependencyUnavailableError,
    IdempotencyMismatchError,
    NotFoundError,
    StaleRevisionError,
)
from app.schemas.core import AgentActionCreate, AgentConflictCheckRequest
from app.schemas.enums import AgentActionType, ErrorCode
from scripts import export_contracts as export

BASE = "http://core.test"
TOKEN = "header.payload.signature"
CTX = CallContext(request_id="req-42", delegation_token=TOKEN)
EXAMPLES = export.CONTRACTS / "examples"
OPENAPI = yaml.safe_load((export.CONTRACTS / "core-api.openapi.yaml").read_text())


def example(name: str) -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(Path(EXAMPLES / name).read_text())
    return loaded


def envelope(code: ErrorCode, message: str = "refused") -> dict[str, Any]:
    return {"code": code.value, "message": message, "details": [], "request_id": "req-42"}


@pytest.fixture
async def http() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(base_url=BASE) as client:
        yield client


@pytest.fixture
def core(http: httpx.AsyncClient) -> HttpCoreClient:
    return HttpCoreClient(http)


def declared(method: str, path: str) -> bool:
    """True when the OpenAPI document declares this method on a template matching `path`."""
    for template, operations in OPENAPI["paths"].items():
        pattern = "^" + re.sub(r"\{[^}]+\}", "[^/]+", template) + "$"
        if re.match(pattern, path) and method.lower() in operations:
            return True
    return False


CHECK = AgentConflictCheckRequest(club_id=uuid4())
ACTION = AgentActionCreate(type=AgentActionType.CREATE_EVENT_DRAFT, summary="Draft a robotics demo")


# ---- the paths are the contract's ------------------------------------------------------


@respx.mock
async def test_every_operation_the_client_calls_is_declared_by_core(core: HttpCoreClient) -> None:
    event = example("event-created.response.json")["event"]
    respx.post(f"{BASE}/internal/v1/agent-tools/check_event_conflicts").respond(
        json=example("conflict-check.response.json")
    )
    respx.get(url__regex=rf"{BASE}/internal/v1/agent-tools/events/.+").respond(json=event)
    respx.post(f"{BASE}/internal/v1/agent-actions").respond(
        201, json=example("agent-action.proposed.json")
    )

    await core.check_event_conflicts(CHECK, CTX)
    await core.get_event_details(UUID(event["id"]), CTX)
    await core.file_agent_action(ACTION, CTX, "key-1")

    sent = [(call.request.method, call.request.url.path) for call in respx.calls]
    assert len(sent) == 3
    for method, path in sent:
        assert declared(method, path), f"{method} {path} is not in core-api.openapi.yaml"


# ---- what goes on the wire -------------------------------------------------------------


@respx.mock
async def test_the_delegation_token_and_request_id_are_forwarded_unmodified(
    core: HttpCoreClient,
) -> None:
    route = respx.post(f"{BASE}/internal/v1/agent-tools/check_event_conflicts").respond(
        json=example("conflict-check.response.json")
    )
    await core.check_event_conflicts(CHECK, CTX)
    headers = route.calls.last.request.headers
    assert headers["authorization"] == f"Bearer {TOKEN}"
    assert headers["x-request-id"] == "req-42"
    assert "idempotency-key" not in headers


@respx.mock
async def test_filing_an_action_sends_the_idempotency_key(core: HttpCoreClient) -> None:
    route = respx.post(f"{BASE}/internal/v1/agent-actions").respond(
        201, json=example("agent-action.proposed.json")
    )
    await core.file_agent_action(ACTION, CTX, "turn-7-call-1")
    assert route.calls.last.request.headers["idempotency-key"] == "turn-7-call-1"


@respx.mock
async def test_an_explicit_null_venue_survives_and_an_omitted_one_stays_omitted(
    core: HttpCoreClient,
) -> None:
    """Core reads null as 'no venue' and omitted as 'keep the stored one'; they must not merge."""
    route = respx.post(f"{BASE}/internal/v1/agent-tools/check_event_conflicts").respond(
        json=example("conflict-check.response.json")
    )
    event_id = uuid4()
    await core.check_event_conflicts(
        AgentConflictCheckRequest(event_id=event_id, resource_id=None), CTX
    )
    await core.check_event_conflicts(AgentConflictCheckRequest(event_id=event_id), CTX)
    cleared, kept = (json.loads(call.request.content) for call in route.calls)
    assert cleared == {"event_id": str(event_id), "resource_id": None}
    assert kept == {"event_id": str(event_id)}


# ---- how Core's refusals are understood ------------------------------------------------


@pytest.mark.parametrize(
    ("status", "body", "expected"),
    [
        (401, envelope(ErrorCode.UNAUTHENTICATED), DeniedError),
        (403, envelope(ErrorCode.FORBIDDEN), DeniedError),
        (404, envelope(ErrorCode.NOT_FOUND), NotFoundError),
        (409, envelope(ErrorCode.STALE_REVISION), StaleRevisionError),
        (422, envelope(ErrorCode.IDEMPOTENCY_MISMATCH), IdempotencyMismatchError),
        (500, envelope(ErrorCode.INTERNAL_ERROR), DependencyUnavailableError),
        (503, envelope(ErrorCode.DEPENDENCY_UNAVAILABLE), DependencyUnavailableError),
    ],
)
@respx.mock
async def test_core_refusals_become_typed_port_errors(
    core: HttpCoreClient, status: int, body: dict[str, Any], expected: type[Exception]
) -> None:
    respx.post(f"{BASE}/internal/v1/agent-actions").respond(status, json=body)
    with pytest.raises(expected):
        await core.file_agent_action(ACTION, CTX, "key-1")


@respx.mock
async def test_a_non_json_gateway_error_is_a_dependency_failure(core: HttpCoreClient) -> None:
    respx.get(url__regex=rf"{BASE}/internal/v1/agent-tools/events/.+").respond(
        502, text="<html>bad gateway</html>"
    )
    with pytest.raises(DependencyUnavailableError):
        await core.get_event_details(uuid4(), CTX)


@respx.mock
async def test_an_unreachable_core_is_a_dependency_failure(core: HttpCoreClient) -> None:
    respx.post(f"{BASE}/internal/v1/agent-tools/check_event_conflicts").mock(
        side_effect=httpx.ConnectError("refused")
    )
    with pytest.raises(DependencyUnavailableError):
        await core.check_event_conflicts(CHECK, CTX)


@respx.mock
async def test_a_success_body_that_breaks_the_contract_is_a_violation(
    core: HttpCoreClient,
) -> None:
    respx.get(url__regex=rf"{BASE}/internal/v1/agent-tools/events/.+").respond(
        json={"id": "not-an-event"}
    )
    with pytest.raises(ContractViolationError):
        await core.get_event_details(uuid4(), CTX)
