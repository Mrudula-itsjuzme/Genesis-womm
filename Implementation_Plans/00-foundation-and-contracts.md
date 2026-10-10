# Implementation Plan 00: Foundation and Contracts

**Status:** In progress. Backend and AI part complete on `backend-ai` (uncommitted); RAG API and Web pending  
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

## Backend and AI execution (branch `backend-ai`)

**Scope:** Core API and Agent API skeletons, their contracts, fakes, `.gitignore`, `.env.example` and a Compose file for `postgres`, `migrate`, `core-api` and `agent-api`. RAG API and Web skeletons stay with their owners and join Compose later. Governing decisions: `docs/architecture/architecture-campuscue-backend-ai-2026-10-10/ARCHITECTURE-SPINE.md` (AD-2, AD-3, AD-8, AD-17 to AD-22).

**Approach:** OpenAPI is exported from code (AD-18), not hand-written. Routes beyond `/health` and `/ready` exist as typed stubs that return the standard envelope with HTTP 501 `NOT_IMPLEMENTED` (AGENTS.md 10.7.3), so Web and Agent get the real request/response schemas now. Each later plan replaces a stub with an implementation without changing its schema. Empty `__init__.py` files travel with their package and do not count toward the 2–3 file limit.

| Batch | Files | Commit |
|---|---|---|
| B1 | `.gitignore`, `.env.example` | `chore(infra): ignore env files and add example settings` |
| B2 | `services/core-api/pyproject.toml`, `uv.lock`, `ruff.toml` | `chore(core): scaffold core-api project and tooling` |
| B3 | `app/domain/enums.py`, `app/domain/time.py`, `tests/unit/test_domain_primitives.py` | `feat(core): add domain enums and clock primitives` |
| B4a | `.importlinter`, `app/domain/ruff.toml`, `app/services/ruff.toml` | `chore(core): enforce hexagonal layering and ban ambient time` |
| B4b | `tests/unit/test_architecture_guards.py`, `Makefile` | `test(core): prove layering and ruff guards fire` |
| B5 | `app/settings.py`, `app/logging.py`, `tests/unit/test_settings.py` | `feat(core): add typed settings and json logging` |
| B6a | `app/schemas/common.py`, `app/api/errors.py`, `tests/unit/test_errors.py` | `feat(core): add error envelope and handlers` |
| B6b | `app/api/middleware.py`, `tests/unit/test_request_id.py` | `feat(core): add request id middleware and access log` |
| B7a | `app/services/readiness.py`, `tests/unit/test_readiness.py` | `feat(core): add readiness evaluation` |
| B7b | `alembic.ini`, `migrations/env.py`, `migrations/script.py.mako` | `chore(core): add alembic scaffolding` |
| B7c | `app/models/base.py`, `migrations/versions/0001_create_schemas.py`, `app/repositories/health.py` | `feat(core): add baseline migration and readiness probe` |
| B8 | `app/main.py`, `app/container.py`, `app/api/routes/health.py` (+ `tests/unit/test_health_routes.py`) | `feat(core): serve health and ready endpoints` |
| B9 | `tests/conftest.py`, `tests/integration/test_migrations.py` | `test(core): verify migrations on postgres 18` |
| B10a | `app/schemas/events.py`, `app/schemas/resources.py`, `app/schemas/agent.py` | `feat(core): define event, resource and agent wire schemas` |
| B10b | `app/api/routes/events.py`, `app/api/routes/resources.py` | `feat(core): add typed event and resource stubs` |
| B10c | `app/api/routes/agent.py`, `app/api/routes/internal.py` | `feat(core): add typed agent and facade stubs` |
| B11 | `scripts/export_contracts.py`, `contracts/core-api.openapi.yaml`, `contracts/schemas/shared.schema.json` | `feat(contracts): export core openapi and shared schemas` |
| B12a | `contracts/examples/` (error, conflict, agent action, citation) | `docs(contracts): add shared payload examples` |
| B12b | `contracts/examples/` (event, conflict-check, agent chat), `tests/contract/test_examples.py` | `test(contracts): validate examples against schemas` |
| B13 | `services/core-api/Dockerfile`, `.dockerignore` | `chore(core): add container image` |
| A1 | `services/agent-api/pyproject.toml`, `uv.lock`, `ruff.toml` | `chore(agent): scaffold agent-api project and tooling` |
| A2 | `.importlinter`, `Makefile` | `chore(agent): enforce port and adapter layering` |
| A3 | `app/settings.py`, `app/logging.py`, `tests/test_settings.py` | `feat(agent): add typed settings and json logging` |
| A4 | `app/schemas/common.py`, `app/api/errors.py`, `app/api/middleware.py` (+ tests) | `feat(agent): add error envelope and request id` |
| A5 | `app/ports/core.py`, `app/ports/rag.py`, `app/clients/fakes.py` | `feat(agent): add core and rag ports with fakes` |
| A6 | `app/main.py`, `app/api/routes/health.py` (+ tests) | `feat(agent): serve health and ready endpoints` |
| A7 | `app/schemas/agent.py`, `app/api/routes/agent.py` (+ tests) | `feat(agent): add typed chat, plan and analyze stubs` |
| A8 | `scripts/export_contracts.py`, `contracts/agent-api.openapi.yaml`, `tests/contract/test_contract.py` | `feat(contracts): export agent openapi` |
| A9 | `services/agent-api/Dockerfile`, `.dockerignore` | `chore(agent): add container image` |
| I1 | `docker-compose.yml`, `README.md` (backend and AI section) | `chore(infra): add compose for postgres, core and agent` |

**Verification per service:** `make verify` runs pytest, `ruff check`, `ruff format --check`, `mypy`, `lint-imports`, and the contract-drift check (`python -m scripts.export_contracts --check`). Core also asserts exactly one Alembic head. Core's `make verify-fast` skips the PostgreSQL tests.

### Execution record (2026-10-10, branch `backend-ai`)

**Status:** Core and Agent skeletons, contracts, fakes, container images and Compose are built and verified. **Nothing is committed yet**; the table above is the proposed commit grouping. RAG and Web skeletons are untouched.

**Evidence** (each command run, exit code 0):

| Check | Result |
|---|---|
| `services/agent-api: make verify` | 175 passed; ruff, ruff format, mypy (45 files), 9 import-linter contracts, contract drift all clean |
| `services/core-api: make verify-fast` | 218 passed, 11 deselected; ruff, ruff format, mypy (52 files), 8 import-linter contracts, contract drift all clean |
| `services/core-api: make verify` | adds 11 PostgreSQL 18 tests (testcontainers): Alembic 1.20 + SQLAlchemy 2.1.4 upgrade, idempotency, downgrade, `alembic check`, `DATABASE_URL`-only one-shot, offline SQL |
| `docker compose up --build` | postgres healthy, `migrate` exit 0, `core-api` and `agent-api` healthy; `/health`, `/ready` verified over HTTP |
| Failure drill | database stopped: Core `/health` 200, `/ready` 503 with the envelope and failed checks, Agent unaffected; recovered on its own after restart |
| Secret separation (names only) | Core holds the signing keys and no `GROQ_API_KEY`; Agent holds `GROQ_API_KEY` and no signing key; both run as UID 10001; 0 matches in all service logs for the injected test token, a query-string secret, the `gsk_` key prefix and the placeholder keys |
| Mutation checks | 9 deliberate breakages (writable `status`, missing stub marker, dropped delegation dependency, extra fields allowed, a confirmation action type, shortened buffer, "free" wording, `Z` timestamp, review flag off) each failed the intended test |

**Deviations from the table above** (none breaks a 2–3 file batch once `__init__.py` files are excluded):
- B6b before B6a: the error envelope needs the request id, so middleware and logging landed first.
- B7 became four steps (models and migration, Alembic config, readiness probe, integration tests), and B8 split into schemas/routes and container/main.
- Added to the plan's scope: `ErrorCode.METHOD_NOT_ALLOWED` (a 405 must not read as a validation error); enums `ResourceKind`, `FreshnessState`, `ToolOutcome`; `Conflict` and `AgentAction` as the canonical schema names (renamed from `*Out`); Agent `ruff.strict.toml`; dev dependencies `httpx2` (Starlette's `TestClient` deprecates `httpx`) and `types-jsonschema`.
- Core `app.settings` has no `campus_timezone`: the wire timezone is fixed in `schemas` and `schemas` may not import settings.
- Postgres is deliberately not published to the host in Compose (another local container owns 5432).
- Test faults found and fixed during the run, not product defects: a Hypothesis strategy generating nonexistent DST local times; an assertion matching `"42"` inside a latency value; three Agent contract tests that compared against components the Agent does not expose.

**Not done, by design:** real HTTP clients for Core and RAG, the model provider and the orchestration loop (Plan 03); actor resolution and authorization behind the declared security schemes (Plan 01); the conflict engine and any event persistence (Plan 01); `contracts/rag-api.openapi.yaml`, `services/rag-api`, `apps/web` (their owners). The Agent's RAG schemas mirror `docs/superpowers/plans/2026-10-10-rag-service.md` and must be corrected when the RAG owner publishes a contract.

## Risks
- Contract churn can block parallel development.
- A readiness endpoint that requires every optional dependency can make healthy services appear unavailable.
- Choosing frameworks late can create duplicate scaffolding.

## Deviation log
- 2026-10-10: Initial proposed plan. Update when repository and stack choices are confirmed.
- 2026-10-10: Stack confirmed for Core and Agent by the backend/AI owner (Python 3.12, FastAPI, PostgreSQL 18; see the architecture spine). Added the "Backend and AI execution" section. Differences from the original steps: OpenAPI is generated from code instead of hand-written (spine AD-18); only Core and Agent skeletons are in scope on `backend-ai`; RAG and Web skeletons and their OpenAPI files belong to their owners.
