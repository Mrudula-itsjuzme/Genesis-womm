# Implementation Plans Index

Detailed implementation plans are required before coding a non-trivial feature.

| Plan | Scope | Main output |
|---|---|---|
| `00-foundation-and-contracts.md` | Repository skeleton and interfaces | Runnable service skeletons, OpenAPI and mocks |
| `01-core-scheduling-and-events.md` | Core API and scheduling | Transaction-safe event rules and auditable state |
| `02-rag-hybrid-retrieval.md` | RAG service | Hybrid retrieval, citations and evaluation |
| `03-agent-tools-and-orchestration.md` | Agent service | Bounded tools and structured action drafts |
| `04-frontend-vertical-slice.md` | Frontend | Primary end-to-end demo experience |

Each plan includes objectives, preconditions, exact expected files, ordered steps, contracts, acceptance criteria, risks and a deviation log. Update plans when implementation reveals a necessary change. Keep `PLAN.md` as the master roadmap rather than duplicating detailed steps there.
