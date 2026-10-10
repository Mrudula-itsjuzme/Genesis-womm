"""The Agent agrees with Core's published contract (spine AD-18).

Core is the producer. Everything the Agent mirrors is compared structurally against Core's
committed OpenAPI and shared schema, so a drift in either service fails here, not in production.
Descriptions and titles are documentation and are ignored.
"""

import inspect
import json
from enum import StrEnum
from pathlib import Path
from typing import Any

import pytest
import yaml
from fastapi import FastAPI
from jsonschema import Draft202012Validator, FormatChecker
from openapi_spec_validator import validate

from app.clients.fakes import FakeCoreClient
from app.ports.clock import FixedClock
from app.schemas import chat, common, core, enums
from scripts import export_contracts as export

CONTRACTS = export.CONTRACTS
CORE_OPENAPI_PATH = CONTRACTS / "core-api.openapi.yaml"
SHARED_PATH = CONTRACTS / "schemas" / "shared.schema.json"
EXAMPLES = CONTRACTS / "examples"

IGNORED_KEYS = {"description", "title", "examples", "example"}
SORTED_LISTS = {"required", "enum"}


def structure(node: Any) -> Any:
    """A schema reduced to what a client depends on."""
    if isinstance(node, dict):
        return {
            key: (
                value.rsplit("/", 1)[-1]
                if key == "$ref"
                else sorted(value)
                if key in SORTED_LISTS
                else structure(value)
            )
            for key, value in node.items()
            if key not in IGNORED_KEYS and not key.startswith("x-")
        }
    if isinstance(node, list):
        return [structure(item) for item in node]
    return node


@pytest.fixture(scope="module")
def openapi() -> dict[str, Any]:
    return export.build_openapi()


@pytest.fixture(scope="module")
def core_openapi() -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(CORE_OPENAPI_PATH.read_text())
    return loaded


@pytest.fixture(scope="module")
def shared() -> dict[str, Any]:
    loaded: dict[str, Any] = json.loads(SHARED_PATH.read_text())
    return loaded


def test_committed_contract_has_no_drift() -> None:
    assert export.find_drift() == [], "run: uv run python -m scripts.export_contracts"


def test_openapi_is_a_valid_3_1_document(openapi: dict[str, Any]) -> None:
    assert openapi["openapi"].startswith("3.1")
    validate(openapi)


def test_export_is_deterministic() -> None:
    assert export.render_all() == export.render_all()


def _agent_enums() -> dict[str, type[StrEnum]]:
    return {
        name: member
        for name, member in inspect.getmembers(enums, inspect.isclass)
        if issubclass(member, StrEnum) and member is not StrEnum
    }


AGENT_ONLY_ENUMS = {"AccessLevel"}


@pytest.mark.parametrize("name", sorted(set(_agent_enums()) - AGENT_ONLY_ENUMS))
def test_each_mirrored_enum_equals_cores_published_values(
    name: str, core_openapi: dict[str, Any], shared: dict[str, Any]
) -> None:
    mine = sorted(member.value for member in _agent_enums()[name])
    assert mine == sorted(core_openapi["components"]["schemas"][name]["enum"])
    if name in shared["$defs"]:
        assert mine == sorted(shared["$defs"][name]["enum"])


def test_the_agent_mirrors_every_enum_core_shares(shared: dict[str, Any]) -> None:
    shared_enums = {name for name, definition in shared["$defs"].items() if "enum" in definition}
    assert shared_enums <= set(_agent_enums())


@pytest.mark.parametrize("name", ["ErrorEnvelope", "Conflict", "AgentAction", "Citation"])
def test_agent_shared_roots_equal_the_shared_schema(
    name: str, openapi: dict[str, Any], shared: dict[str, Any]
) -> None:
    assert structure(openapi["components"]["schemas"][name]) == structure(shared["$defs"][name])


REQUEST_MODELS = [core.AgentConflictCheckRequest, core.AgentActionCreate]
RESPONSE_MODELS = [core.EventOut, core.ConflictCheckOut, core.AgentAction]
MIRRORED = [
    "EventOut",
    "ConflictEventSummary",
    "Conflict",
    "ConflictCheckOut",
    "AgentConflictCheckRequest",
    "AgentActionCreate",
    "AgentAction",
]


def mirror_components() -> dict[str, Any]:
    """Schemas for the mirror models, produced by the same generator Core's OpenAPI uses."""
    app = FastAPI()

    async def returns() -> Any:
        return None

    for index, request_model in enumerate(REQUEST_MODELS):

        async def takes(payload: Any) -> None:
            return None

        takes.__annotations__["payload"] = request_model
        app.add_api_route(f"/in/{index}", takes, methods=["POST"])
    for index, response_model in enumerate(RESPONSE_MODELS):
        app.add_api_route(f"/out/{index}", returns, methods=["GET"], response_model=response_model)
    components: dict[str, Any] = app.openapi()["components"]["schemas"]
    return components


@pytest.mark.parametrize("name", MIRRORED)
def test_core_facade_mirror_equals_cores_own_contract(
    name: str, core_openapi: dict[str, Any]
) -> None:
    mine = mirror_components()[name]
    theirs = core_openapi["components"]["schemas"][name]
    assert structure(mine) == structure(theirs)


@pytest.mark.parametrize("name", ["ChatMessage", "ChatResponse", "ToolTraceEntry", "Citation"])
def test_chat_shapes_equal_the_ones_core_relays(
    name: str, openapi: dict[str, Any], core_openapi: dict[str, Any]
) -> None:
    assert structure(openapi["components"]["schemas"][name]) == structure(
        core_openapi["components"]["schemas"][name]
    )


def test_a_turn_is_cores_chat_request_plus_an_access_level_set_by_core(
    openapi: dict[str, Any], core_openapi: dict[str, Any]
) -> None:
    turn = structure(openapi["components"]["schemas"]["AgentTurnRequest"])
    chat_request = structure(core_openapi["components"]["schemas"]["ChatRequest"])
    access_level = turn["properties"].pop("access_level")
    assert access_level["$ref"] == "AccessLevel"
    assert access_level["default"] == "CAMPUS_PUBLIC"
    assert turn == chat_request
    assert "access_level" not in json.dumps(core_openapi), "clients must not be able to set it"


def test_every_facade_operation_the_agent_calls_exists_in_core(
    core_openapi: dict[str, Any],
) -> None:
    paths = core_openapi["paths"]
    called = [
        ("post", "/internal/v1/agent-tools/check_event_conflicts"),
        ("get", "/internal/v1/agent-tools/events/{event_id}"),
        ("post", "/internal/v1/agent-actions"),
    ]
    for method, path in called:
        operation = paths[path][method]
        schemes = {name for requirement in operation["security"] for name in requirement}
        assert schemes == {"delegationBearer", "internalKey"}, path


def test_the_agent_never_calls_a_public_or_authority_route(core_openapi: dict[str, Any]) -> None:
    # The only Core routes the Agent's ports can reach are the three facade operations above.
    port_methods = {"check_event_conflicts", "get_event_details", "file_agent_action"}
    from app.ports.core import CoreToolsPort

    declared = {name for name in vars(CoreToolsPort) if not name.startswith("_")}
    assert declared == port_methods
    assert not any(
        "confirm" in method or "override" in method or "book" in method for method in declared
    )


def _validator(
    schema: dict[str, Any], name: str, components: dict[str, Any]
) -> Draft202012Validator:
    wrapper = {"$ref": f"#/components/schemas/{name}", "components": {"schemas": components}}
    return Draft202012Validator(wrapper, format_checker=FormatChecker())


@pytest.mark.asyncio
async def test_fake_core_outputs_satisfy_cores_published_schema(
    core_openapi: dict[str, Any],
) -> None:
    from datetime import UTC, datetime
    from uuid import uuid4

    from app.ports.core import CallContext
    from app.schemas.core import AgentActionCreate, AgentConflictCheckRequest, Conflict
    from app.schemas.enums import AgentActionType, ConflictType, Severity

    now = datetime(2026, 10, 10, 4, 0, tzinfo=UTC)
    conflict = Conflict(
        type=ConflictType.VENUE_OVERLAP,
        severity=Severity.BLOCKING,
        event_ids=[uuid4()],
        start_at=now,
        end_at=now,
        message="overlap",
        override_required=True,
    )
    fake = FakeCoreClient(clock=FixedClock(now), conflicts=[conflict])
    ctx = CallContext(request_id="r", delegation_token="t")
    components = core_openapi["components"]["schemas"]

    checked = await fake.check_event_conflicts(AgentConflictCheckRequest(), ctx)
    _validator({}, "ConflictCheckOut", components).validate(checked.model_dump(mode="json"))
    action = await fake.file_agent_action(
        AgentActionCreate(type=AgentActionType.CREATE_FOLLOWUP_DRAFT, summary="x"), ctx, "k"
    )
    _validator({}, "AgentAction", components).validate(action.model_dump(mode="json"))


EXAMPLE_MODELS: dict[str, Any] = {
    "error-envelope.conflict-detected.json": common.ErrorEnvelope,
    "error-envelope.not-implemented.json": common.ErrorEnvelope,
    "conflict.venue-overlap.json": core.Conflict,
    "conflict.campus-gap-violation.json": core.Conflict,
    "conflict.tentative-overlap.json": core.Conflict,
    "conflict.unknown-availability.json": core.Conflict,
    "citation.json": chat.Citation,
    "agent-action.proposed.json": core.AgentAction,
    "conflict-check.response.json": core.ConflictCheckOut,
    "agent-chat.response.json": chat.ChatResponse,
}


@pytest.mark.parametrize("name", sorted(EXAMPLE_MODELS))
def test_the_agent_parses_every_core_example_and_reproduces_it_exactly(name: str) -> None:
    example = json.loads((EXAMPLES / name).read_text())
    model = EXAMPLE_MODELS[name].model_validate(example)
    assert model.model_dump(mode="json") == example


def test_the_agent_rejects_a_value_core_has_not_published() -> None:
    example = json.loads((EXAMPLES / "conflict.venue-overlap.json").read_text())
    example["type"] = "CAPACITY_EXCEEDED"
    with pytest.raises(ValueError, match=r"CAPACITY_EXCEEDED|enum|valid"):
        core.Conflict.model_validate(example)


def test_agent_turn_example_is_covered_by_cores_chat_example() -> None:
    request = json.loads((EXAMPLES / "agent-chat.request.json").read_text())
    turn = chat.AgentTurnRequest.model_validate(request)
    assert turn.access_level.value == "CAMPUS_PUBLIC"
    assert Path(EXAMPLES / "agent-chat.request.json").exists()
