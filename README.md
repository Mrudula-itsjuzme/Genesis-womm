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

### Running RAG API Service

```bash
cd services/rag-api
pip install -e .
uvicorn app.main:app --port 8002 --reload
```

Run tests:
```bash
pytest services/rag-api/tests/ -v
```

## Product truth
A tentative event is not a booking. An acknowledgment is not official confirmation. Empty calendars do not prove availability. LLMs do not own scheduling rules or authorization. An external registration redirect is not proof that a student registered. Synthetic demo data must be labeled as synthetic.
