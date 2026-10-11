# Implementation Plans Index

Detailed implementation plans are required before coding a non-trivial feature.

| Plan | Scope | Main output |
|---|---|---|
| `00-foundation-and-contracts.md` | Repository skeleton and interfaces | Runnable service skeletons, OpenAPI and mocks |
| `01-core-scheduling-and-events.md` | Core API and scheduling | Transaction-safe event rules and auditable state |
| `02-rag-hybrid-retrieval.md` | RAG service | Hybrid retrieval, citations and evaluation |
| `03-agent-tools-and-orchestration.md` | Agent service | Bounded tools and structured action drafts |
| `04-frontend-vertical-slice.md` | Frontend | Primary end-to-end demo experience |
| `05-student-registration-risk.md` | Core API and Frontend | Student discovery, registration, and private mock academic-risk warnings |
| `06-official-source-ingestion.md` | RAG and Core API | Separate policy RAG and structured campus-data ingestion pipelines |
| `08-schedule-change-impact.md` | Core API and Frontend | Implemented: staged schedule changes, deterministic dependency impact and atomic revalidation; final regression results in HANDOFF.md |

Each plan includes objectives, preconditions, exact expected files, ordered steps, contracts, acceptance criteria, risks and a deviation log. Update plans when implementation reveals a necessary change. Keep `PLAN.md` as the master roadmap rather than duplicating detailed steps there.
