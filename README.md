# CampusCue

CampusCue is an AI-assisted event operations workspace for university clubs. It supports tentative event planning, scheduling conflict detection, campus resource discovery, policy-grounded answers, commitment tracking, change-impact analysis, and editable event reports.

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

## Development rule
Before implementing a non-trivial feature, read the three context documents and its implementation plan. If no plan exists, write and review one first.

## Local setup
The repository is at planning stage; concrete commands must be added when the service skeletons and package managers are selected. The intended integrated workflow uses Docker Compose. Each service must also support independent local tests with mocks.

## Product truth
A tentative event is not a booking. An acknowledgment is not official confirmation. Empty calendars do not prove availability. LLMs do not own scheduling rules or authorization. Synthetic demo data must be labeled as synthetic.
