"""The committed contracts are exactly what the code produces (spine AD-18)."""

import json
from typing import Any

import pytest
from jsonschema import Draft202012Validator
from openapi_spec_validator import validate

from scripts import export_contracts as export


@pytest.fixture(scope="module")
def openapi() -> dict[str, Any]:
    return export.build_openapi()


@pytest.fixture(scope="module")
def shared(openapi: dict[str, Any]) -> dict[str, Any]:
    return export.build_shared_schema(openapi)


def test_committed_contracts_have_no_drift() -> None:
    assert export.find_drift() == [], "run: uv run python -m scripts.export_contracts"


def test_openapi_is_a_valid_3_1_document(openapi: dict[str, Any]) -> None:
    assert openapi["openapi"].startswith("3.1")
    validate(openapi)


def test_export_is_deterministic() -> None:
    assert export.render_all() == export.render_all()


def test_shared_schema_is_valid_json_schema(shared: dict[str, Any]) -> None:
    Draft202012Validator.check_schema(shared)


def test_shared_schema_has_the_four_cross_service_roots(shared: dict[str, Any]) -> None:
    assert {"ErrorEnvelope", "Conflict", "AgentAction", "Citation"} <= set(shared["$defs"])


def test_shared_schema_is_self_contained(shared: dict[str, Any]) -> None:
    refs: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "$ref":
                    refs.add(str(value))
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(shared)
    assert refs, "expected internal references"
    for ref in refs:
        assert ref.startswith("#/$defs/"), ref
        assert ref.removeprefix("#/$defs/") in shared["$defs"], ref


def test_shared_definitions_match_openapi_components(
    openapi: dict[str, Any], shared: dict[str, Any]
) -> None:
    components = openapi["components"]["schemas"]
    rewritten = json.loads(json.dumps(components).replace("#/components/schemas/", "#/$defs/"))
    for name, definition in shared["$defs"].items():
        assert definition == rewritten[name], name


def test_openapi_contains_no_localhost_servers_or_secrets(openapi: dict[str, Any]) -> None:
    text = json.dumps(openapi).lower()
    for needle in ("localhost", "signing_key", "password", "bearer ey"):
        assert needle not in text, needle
