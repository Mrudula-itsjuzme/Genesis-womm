# CampusCue

AI-assisted university club event coordination, piloted at Amrita Coimbatore.

> **Tentative interest is not an official hall booking.** CampusCue lets clubs coordinate proposed dates and resources before approvals, then tracks verified commitments, event changes, OSA policy guidance, and event reports.

## Monorepo

- `apps/web`: React/Vite organizer interface
- `apps/api`: FastAPI core backend, resource/event APIs and deterministic conflict rules
- `services/agent`: agent/tool orchestration FastAPI service (initial stub)
- `services/rag`: OSA handbook retrieval FastAPI service (initial stub)
- `docs`: product scope, API contracts, responsibilities and constraints

## Local development

```bash
cp .env.example .env
docker compose up --build
```

Web: http://localhost:5173 · Core API: http://localhost:8000/docs · Agent: http://localhost:8001/docs · RAG: http://localhost:8002/docs

## Start here

The initial scaffold exposes demo data. A missing venue booking is **UNKNOWN**, never automatically **AVAILABLE**. Agent and RAG endpoints are placeholders until real integrations are implemented. Do not put organizer-group exports, private correspondence, tokens, real approvals or participant data in this public repository.

Design proposal: [CampusCue project blueprint](https://docs.google.com/document/d/1-axjLwz6vFbnuPxJhyBFU80SKwm-xnpJJ31kLGHDfLQ/edit).

## Branch ownership

- `feat/ui`: organizer interface
- `feat/core-api`: structured events, resources and workflow
- `feat/agent`: AI agent and tool calls
- `feat/rag`: handbook parsing, retrieval and citations

Define contracts early; integrate continuously through pull requests.