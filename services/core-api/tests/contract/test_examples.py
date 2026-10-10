"""Every example under contracts/examples is valid, canonical and says the right thing."""

import json
from datetime import datetime, timedelta
from typing import Any

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from pydantic import BaseModel

from app.schemas import agent, common, events
from scripts import export_contracts as export

EXAMPLES_DIR = export.CONTRACTS / "examples"

# example file -> (OpenAPI component, Pydantic model)
EXAMPLES: dict[str, tuple[str, type[BaseModel]]] = {
    "error-envelope.conflict-detected.json": ("ErrorEnvelope", common.ErrorEnvelope),
    "error-envelope.not-implemented.json": ("ErrorEnvelope", common.ErrorEnvelope),
    "conflict.venue-overlap.json": ("Conflict", events.Conflict),
    "conflict.campus-gap-violation.json": ("Conflict", events.Conflict),
    "conflict.tentative-overlap.json": ("Conflict", events.Conflict),
    "conflict.unknown-availability.json": ("Conflict", events.Conflict),
    "citation.json": ("Citation", agent.Citation),
    "agent-action.proposed.json": ("AgentAction", agent.AgentAction),
    "event-create.request.json": ("EventCreate", events.EventCreate),
    "event-created.response.json": ("EventCreatedOut", events.EventCreatedOut),
    "conflict-check.response.json": ("ConflictCheckOut", events.ConflictCheckOut),
    "agent-chat.request.json": ("ChatRequest", agent.ChatRequest),
    "agent-chat.response.json": ("ChatResponse", agent.ChatResponse),
}
SHARED_ROOTS = {"ErrorEnvelope", "Conflict", "AgentAction", "Citation"}


def load(name: str) -> Any:
    return json.loads((EXAMPLES_DIR / name).read_text())


@pytest.fixture(scope="module")
def openapi() -> dict[str, Any]:
    return export.build_openapi()


@pytest.fixture(scope="module")
def shared(openapi: dict[str, Any]) -> dict[str, Any]:
    return export.build_shared_schema(openapi)


def test_every_example_file_is_registered_and_every_registration_exists() -> None:
    on_disk = {p.name for p in EXAMPLES_DIR.glob("*.json")}
    assert on_disk == set(EXAMPLES)


@pytest.mark.parametrize("name", sorted(EXAMPLES))
def test_example_validates_against_the_openapi_component(
    name: str, openapi: dict[str, Any]
) -> None:
    component, _ = EXAMPLES[name]
    schema = {
        "$ref": f"#/components/schemas/{component}",
        "components": openapi["components"],
    }
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(load(name))


@pytest.mark.parametrize("name", sorted(n for n, (c, _) in EXAMPLES.items() if c in SHARED_ROOTS))
def test_shared_example_validates_against_the_shared_schema(
    name: str, shared: dict[str, Any]
) -> None:
    component, _ = EXAMPLES[name]
    schema = {"$ref": f"#/$defs/{component}", "$defs": shared["$defs"]}
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(load(name))


@pytest.mark.parametrize("name", sorted(EXAMPLES))
def test_example_is_in_canonical_wire_form(name: str) -> None:
    _, model = EXAMPLES[name]
    example = load(name)
    assert model.model_validate(example).model_dump(mode="json") == example


def _all_datetimes(node: Any) -> list[str]:
    found: list[str] = []
    if isinstance(node, dict):
        for key, value in node.items():
            if key.endswith("_at") and isinstance(value, str):
                found.append(value)
            else:
                found += _all_datetimes(value)
    elif isinstance(node, list):
        for item in node:
            found += _all_datetimes(item)
    return found


@pytest.mark.parametrize("name", sorted(EXAMPLES))
def test_times_are_shown_in_campus_time(name: str) -> None:
    for value in _all_datetimes(load(name)):
        assert value.endswith("+05:30"), f"{name}: {value}"


def test_venue_overlap_is_blocking_and_needs_an_override() -> None:
    conflict = load("conflict.venue-overlap.json")
    assert (conflict["type"], conflict["severity"]) == ("VENUE_OVERLAP", "blocking")
    assert conflict["constraint"] == "VENUE_OVERLAP"
    assert conflict["override_required"] is True


def test_campus_gap_buffer_is_the_gap_after_the_event_that_starts_first() -> None:
    conflict = load("conflict.campus-gap-violation.json")
    assert (conflict["type"], conflict["severity"]) == ("CAMPUS_GAP_VIOLATION", "blocking")
    assert conflict["constraint"] == "CAMPUS_GAP"
    other = conflict["with_event"]
    buffer_start = datetime.fromisoformat(conflict["start_at"])
    buffer_end = datetime.fromisoformat(conflict["end_at"])
    assert buffer_start == datetime.fromisoformat(other["end_at"])
    assert buffer_end - buffer_start == timedelta(minutes=120)
    assert other["status"] == "CONFIRMED"


def test_tentative_overlap_is_a_warning_that_blocks_nothing() -> None:
    conflict = load("conflict.tentative-overlap.json")
    assert (conflict["type"], conflict["severity"]) == ("TENTATIVE_OVERLAP", "warning")
    assert conflict["override_required"] is False
    assert conflict["with_event"]["status"] != "CONFIRMED"
    assert conflict["constraint"] in {"VENUE_OVERLAP", "CAMPUS_GAP"}


def test_unknown_availability_is_informational_and_never_says_free() -> None:
    conflict = load("conflict.unknown-availability.json")
    assert (conflict["type"], conflict["severity"]) == ("UNKNOWN_AVAILABILITY", "info")
    assert conflict["override_required"] is False
    assert len(conflict["event_ids"]) == 1
    assert "free" not in conflict["message"].lower()
    assert "available" in conflict["message"].lower()


def test_overlapping_events_violate_both_constraints_independently() -> None:
    check = load("conflict-check.response.json")
    types = {c["type"] for c in check["conflicts"]}
    assert {"VENUE_OVERLAP", "CAMPUS_GAP_VIOLATION"} <= types
    assert check["advisory"] is True
    assert check["has_blocking"] is True


def test_saving_a_draft_reports_conflicts_without_blocking_the_save() -> None:
    created = load("event-created.response.json")
    assert created["event"]["status"] == "DRAFT"
    assert created["event"]["venue_availability"] == "UNKNOWN"
    assert created["event"]["synthetic"] is True
    assert {c["type"] for c in created["conflicts"]} == {"UNKNOWN_AVAILABILITY"}


def test_create_request_has_no_status_or_authority_fields() -> None:
    request = load("event-create.request.json")
    assert {"status", "authorized_by", "revision", "id"}.isdisjoint(request)


def test_conflict_error_embeds_a_conflict_in_details() -> None:
    envelope = load("error-envelope.conflict-detected.json")
    assert envelope["code"] == "CONFLICT_DETECTED"
    assert envelope["details"]
    for detail in envelope["details"]:
        events.Conflict.model_validate(detail)


def test_agent_action_is_only_a_proposal() -> None:
    action = load("agent-action.proposed.json")
    assert action["status"] == "PROPOSED"
    assert action["requires_human_review"] is True


def test_agent_reply_speaks_of_proposals_not_completed_work() -> None:
    reply = load("agent-chat.response.json")
    assert reply["proposed_actions"]
    message = reply["message"].lower()
    assert "proposed" in message or "proposal" in message
    for done in ("i booked", "i have booked", "confirmed your", "has been created"):
        assert done not in message
    assert reply["citations"], "the policy claim carries a citation"
    assert all(entry["outcome"] == "OK" for entry in reply["trace"])


def test_examples_are_labelled_synthetic_and_use_no_real_domains() -> None:
    text = "".join((EXAMPLES_DIR / name).read_text() for name in EXAMPLES)
    assert "amrita.edu" not in text
    assert "https://" not in text.replace("https://example.invalid", "")
