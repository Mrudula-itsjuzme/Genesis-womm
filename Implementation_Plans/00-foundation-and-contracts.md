# Implementation Plan 00: Foundation and Contracts

**Status:** Required before parallel feature implementation  
**Owner:** All workstream leads  
**Prerequisites:** Product scope and service boundaries reviewed

## Objective
Create a runnable repository skeleton and stable interfaces so Core, Agent, RAG and frontend teams can develop independently.

## Non-goals
- No production auth integration.
- No live booking integration.
- No full UI feature implementation.
- No claims of university approval.

## Files expected
- `README.md`
- `PROJECT.md`
- `PLAN.md`
- `CONTEXT_ARCHITECTURE.md`
- `AGENTS.md`
- `contracts/core-api.openapi.yaml`
- `contracts/agent-api.openapi.yaml`
- `contracts/rag-api.openapi.yaml`
- `contracts/examples/`
- `docker-compose.yml`
- `services/core-api/`
- `services/agent-api/`
- `services/rag-api/`
- `apps/web/`

## Ordered steps
1. Confirm frontend framework and Core API language.
2. Agree stable IDs, timestamp conventions, error envelope, auth identity and correlation ID.
3. Define event, resource, conflict, commitment, evidence, override, RAG citation and agent action schemas.
4. Add OpenAPI specs and representative success/error examples.
5. Scaffold each service with `/health` and `/ready`.
6. Add independent Dockerfiles and environment variable examples without secrets.
7. Add Docker Compose for local dependencies and services.
8. Add contract tests that validate sample payloads against schemas.
9. Add mock clients/fixtures so Agent and frontend work without real dependencies.
10. Verify each service can run independently and in Compose.

## Contract conventions
- UUID IDs.
- ISO 8601 timezone-aware timestamps.
- `Asia/Kolkata` for campus-facing date/time interpretation and display.
- Stable error envelope: `code`, `message`, `details`, `request_id`.
- Mutation idempotency where retries can duplicate writes.
- Event mutations carry expected revision/version.
- Conflict response types are stable enums, not free-form strings.

## Acceptance criteria
- All service skeletons start independently.
- Health and readiness semantics are documented.
- OpenAPI specs validate.
- Contract fixtures pass.
- No secret values are committed.
- A contributor can understand ownership and run focused tests from README.
- No team depends on an unfinished service to begin its mock-based work.

## Risks
- Contract churn can block parallel development.
- A readiness endpoint that requires every optional dependency can make healthy services appear unavailable.
- Choosing frameworks late can create duplicate scaffolding.

## Deviation log
- 2026-10-10: Initial proposed plan. Update when repository and stack choices are confirmed.
