# Implementation Plan 03: Agent Tools and Orchestration

**Status:** Planned  
**Owner:** Agent workstream  
**Dependencies:** Plan 00 contracts; mocked Core/RAG clients

## Objective
Implement a bounded agent that translates natural-language requests into structured plans, calls typed tools, explains deterministic results and drafts actions without becoming an authority over event state.

## Non-goals
- Direct database access.
- Arbitrary shell, SQL or unrestricted HTTP tools.
- Automatic outbound messages.
- LLM-controlled admin overrides or official confirmations.
- Reporting success when a tool fails.

## Files expected
- `services/agent-api/app/api/routes/chat.py`
- `services/agent-api/app/api/routes/plan_event.py`
- `services/agent-api/app/api/routes/analyze_change.py`
- `services/agent-api/app/orchestration/`
- `services/agent-api/app/tools/`
- `services/agent-api/app/clients/core_api.py`
- `services/agent-api/app/clients/rag_api.py`
- `services/agent-api/app/schemas/`
- `services/agent-api/tests/`

## Initial tool contracts
- `check_event_conflicts`
- `create_event_draft`
- `get_event_details`
- `get_event_timeline`
- `request_event_change`
- `get_change_impact`
- `get_resource_details`
- `search_campus_policy`
- `get_event_checklist`
- `record_commitment` (authorized cases only)
- `create_followup_draft`
- `generate_event_report`

No unrestricted `book_event` tool. Proposal creation and official confirmation are separate operations. Any confirmation capability must be backed by a Core API endpoint with server-side authorization and evidence validation.

## Ordered steps
1. Define agent request/response schemas, action representation and citation format.
2. Add LLM provider interface and a deterministic fake provider for tests.
3. Implement typed Core API and RAG clients with timeouts and structured errors.
4. Register an explicit allowlist of tools.
5. Validate tool arguments with schemas before calling services.
6. Enforce a maximum tool-call count, deadline and output-size limits.
7. Return tool trace entries with tool name, sanitized arguments, outcome and request ID.
8. Add missing-field handling; ask a question rather than guess critical date/time/duration.
9. Implement planning assistance using Core conflict results and RAG evidence.
10. Implement change explanation from deterministic impact data.
11. Implement action drafts that require user review.
12. Add idempotency for mutation tools and expected event revision checks.
13. Add prompt-injection tests using malicious user text and retrieved document passages.
14. Add tests for tool timeout, failure, unauthorized operations, stale data and malformed LLM output.
15. Document provider configuration and mock-based local run.

## Endpoint candidates
- `POST /v1/agent/chat`
- `POST /v1/agent/plan-event`
- `POST /v1/agent/analyze-change`
- `GET /health`
- `GET /ready`

## Definition of done
- Agent calls conflict tools instead of deciding conflicts from prose.
- Policy claims include RAG evidence IDs/citations.
- No tool can bypass Core authorization.
- Failed tools cannot be described as successful.
- Agent requests human confirmation before consequential mutations.
- All responses validate against the schema.
- Tests run with no paid model API using a fake provider.

## Risks
- Unbounded loops and retries.
- Tool outputs may be stale or malformed.
- Retrieved text can contain prompt injection.
- Model provider latency or quota can break demos; retain a deterministic mock/demo path.

## Deviation log
- Initial plan dated 2026-10-10; implementation not started.
