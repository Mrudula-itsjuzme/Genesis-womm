"""Explicit tool allowlist (spine AD-10).

The Agent may only call tools defined here. Any tool name not present in TOOL_SCHEMAS
is rejected before it reaches a port.
"""

from typing import Any

# Each entry is an OpenAI-compatible function tool spec that the LLM sees.
TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "check_event_conflicts",
            "description": (
                "Check for scheduling conflicts at Core. Returns a list of conflicts "
                "and whether any are blocking. Always call this before proposing a time slot."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": (
                            "UUID of an existing event to re-check. Omit for new events."
                        ),
                    },
                    "club_id": {
                        "type": "string",
                        "description": "UUID of the club creating an unsaved event candidate.",
                    },
                    "start_at": {
                        "type": "string",
                        "description": (
                            "ISO-8601 datetime with timezone, e.g. 2026-11-15T10:00:00+05:30."
                        ),
                    },
                    "end_at": {
                        "type": "string",
                        "description": "ISO-8601 datetime with timezone.",
                    },
                    "resource_id": {
                        "type": "string",
                        "description": "UUID of the venue/resource being requested.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_event_details",
            "description": "Fetch the current details and status of an existing event from Core.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "UUID of the event.",
                    },
                },
                "required": ["event_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_campus_policy",
            "description": (
                "Search the OSA handbook and approved campus policy documents. "
                "Returns cited evidence chunks. Use this before making any policy claim."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural-language policy question.",
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "Max results to return (1-10).",
                        "default": 4,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_event_draft_proposal",
            "description": (
                "File a CREATE_EVENT_DRAFT proposal for a human to review and confirm. "
                "Never call this without first checking for conflicts. "
                "Returns a proposal ID; nothing is booked or confirmed."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "One-sentence summary of the proposed event.",
                    },
                    "payload": {
                        "type": "object",
                        "description": (
                            "Event fields the user wants to set (title, start_at, end_at, etc.)."
                        ),
                    },
                },
                "required": ["summary", "payload"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "file_change_request_proposal",
            "description": (
                "File a REQUEST_EVENT_CHANGE proposal for a human to review. "
                "Use this only after explaining the deterministic impact from Core. "
                "Nothing changes until a human confirms."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {
                        "type": "string",
                        "description": "UUID of the event to change.",
                    },
                    "expected_revision": {
                        "type": "integer",
                        "description": (
                            "The revision number the caller read; prevents stale updates."
                        ),
                    },
                    "summary": {
                        "type": "string",
                        "description": "One-sentence summary of what would change.",
                    },
                    "payload": {
                        "type": "object",
                        "description": "Proposed field changes.",
                    },
                },
                "required": ["event_id", "expected_revision", "summary", "payload"],
            },
        },
    },
]

# Fast lookup set for the dispatch guard.
ALLOWED_TOOL_NAMES: frozenset[str] = frozenset(t["function"]["name"] for t in TOOL_SCHEMAS)
