# CampusCue

CampusCue is an AI-assisted event operations workspace for university clubs. It supports tentative event planning, scheduling conflict detection, campus resource discovery, policy-grounded answers, commitment tracking, change-impact analysis, editable event reports, and student event discovery and registration.

## Repository map

```text
PROJECT.md
PLAN.md
CONTEXT_ARCHITECTURE.md
AGENTS.md
Implementation_Plans/
contracts/
prompts/
services/
  core-api/
  agent-api/
  rag-api/
apps/
  web/
```

## Architecture in one minute
- `core-api`: operational source of truth, authorization, event scheduling and audit.
- `agent-api`: bounded tool orchestration and explanations.
- `rag-api`: approved document ingestion, hybrid retrieval and citations.
- `web`: user interface.
- PostgreSQL: operational records and initial sparse/dense retrieval storage.

## Student registration flow

Organizers publish events to a selected student audience and choose internal registration, an external registration link, or an informational-only event. Students see only published events. Before a student registers or is redirected to an external form, CampusCue runs a private academic-risk check against seeded exam and timetable data plus a mock attendance provider.

The check can warn about an exam conflict, an exam on the next day, or a class overlap with low attendance. It is advisory and never makes an institutional attendance-eligibility decision. Calendar, timetable, attendance, and warning data stay visible only to the student. The MVP uses mock academic data; an institutional attendance API requires authorization and a documented integration.

## Development rule
Before implementing a non-trivial feature, read the three context documents and its implementation plan. If no plan exists, write and review one first.

## Local setup

The intended integrated workflow uses Docker Compose. Each service also supports independent local execution and tests with mocks.

`core-api` and `agent-api` are scaffolded (Python 3.12, FastAPI, managed with [uv](https://docs.astral.sh/uv/)). `rag-api` and `web` join Compose when running the integrated system. Design decisions for the backend services live in `docs/architecture/architecture-campuscue-backend-ai-2026-10-10/ARCHITECTURE-SPINE.md`.

### Run the stack

PostgreSQL 18, a one-shot migration, Core on `:8000`, Agent on `127.0.0.1:8001`:

```bash
cp .env.example .env        # development-only placeholders; add GROQ_API_KEY only if you use AGENT_MODEL_PROVIDER=groq
docker compose up --build
curl localhost:8000/health   # liveness
curl localhost:8000/ready    # database reachable and migrations applied
docker compose down -v       # also drops the database volume
```

### Test individual services

No Docker, no network, no paid model required; every dependency has a fake/offline mock:

```bash
# Agent API
cd services/agent-api && make verify        # ruff, mypy, import-linter, pytest, contract drift

# Core API
cd services/core-api  && make verify-fast   # same checks, skipping the PostgreSQL tests
cd services/core-api  && make verify        # also runs the PostgreSQL 18 tests (needs Docker)

# RAG API
cd services/rag-api
pip install -e .
pytest tests/ -v                            # 84 tests, 100% offline
uvicorn app.main:app --port 8002 --reload   # local dev server
```

### Contracts

Contracts are generated from code, so they cannot drift from it. After changing a route or schema:

```bash
cd services/core-api  && uv run python -m scripts.export_contracts
cd services/agent-api && uv run python -m scripts.export_contracts
```

This rewrites `contracts/*.openapi.yaml` and `contracts/schemas/shared.schema.json`. `make verify` fails if they are stale. Routes marked `x-implementation-status: stub` have their final request and response schemas but return `501 NOT_IMPLEMENTED` until their plan lands, so Web and Agent can build against them now. Example payloads are in `contracts/examples/`.

## Product truth
A tentative event is not a booking. An acknowledgment is not official confirmation. Empty calendars do not prove availability. LLMs do not own scheduling rules or authorization. An external registration redirect is not proof that a student registered. Synthetic demo data must be labeled as synthetic.
