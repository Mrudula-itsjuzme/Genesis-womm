# CampusCue Context and Architecture

## 1. Context boundary

CampusCue coordinates organizer workflows around events. It can store proposals and organizer-reported requests, but institutional status is authoritative only when verified evidence comes from an authorized source.

External systems and sources:
- OSA Student Affairs Handbook and other approved policy documents.
- Campus event pages and verified facility/service information.
- The allowlisted Amrita Coimbatore sources in `SOURCE_REGISTRY.md`, split between a reviewed policy corpus and structured campus catalog records.
- Official booking or calendar system, only if access is authorized and integration is approved.
- Student-selected Google Calendar, using read-only access only when the student connects it.
- Mock attendance and timetable providers for the MVP. An institutional academic-record API is not assumed.
- Human organizers and authorized administrators.
- Groq for generation, local dense-embedding model, SPLADE sparse-retrieval model, and a deterministic mock provider for tests.

## 2. Logical architecture

```mermaid
flowchart TB
    UI[Web Frontend]
    CORE[Core API and Scheduling Engine]
    DB[(PostgreSQL)]
    CHROMA[(ChromaDB Vector Store)]
    MINIO[(MinIO S3 Proposal Storage)]
    AGENT[Agent FastAPI]
    RAG[RAG FastAPI]
    DOCS[Approved Documents & Student Handbook]
    LLM[Groq / LLM Provider]
    EMB[Local Embedding Models]

    UI --> CORE
    CORE <--> DB
    CORE <--> MINIO
    CORE --> AGENT
    AGENT --> CORE
    AGENT --> RAG
    AGENT --> LLM
    RAG --> DOCS
    RAG --> CHROMA
    RAG --> EMB
    RAG --> LLM
```

## 2.1 Multi-Stage Proposal Workflow
Proposals follow a deterministic two-stage authorized review pipeline before official institutional booking:
1. **Club Proposal Submission:** Club Organizer files the official Amrita Facility Booking Form and encloses Dean Academic Approval PDF. Proposal enters status `SUBMITTED`.
2. **Stage 1 (Faculty Advisor Endorsement):** The club's designated `FACULTY_ADVISOR` (e.g. *Dr. S. Mahadevan* for Intel IoT Club) reviews the proposal document and endorses/approves it (`APPROVED` stage 1).
3. **Stage 2 (Campus Admin / OSA Final Confirmation):** Campus Admin conducts final institutional review, checks deterministic venue overlaps and 120-minute campus gaps, records verification evidence, and confirms the event. On final approval, the proposal document is automatically indexed into RAG (`CHUNKED`) via MinIO presigned transfer.

## 3. Service ownership

### Core API
Owns operational records and decisions:
- identity/authorization integration;
- clubs, memberships, events, resources;
- event publication, internal registrations, and external-registration redirects;
- student-private timetable, academic-calendar, and mock-attendance records used for registration-risk checks;
- schedule validation and transaction-safe conflict prevention;
- event revisions, commitments, evidence references, dependencies, tasks;
- scoped administrator overrides and audit history;
- verified data assembly for reports.

### Agent API
Owns reasoning orchestration for one interaction:
- natural-language intent extraction;
- tool selection and bounded execution;
- calling Core API and RAG;
- explaining structured results;
- producing action drafts and report text;
- trace and structured response output.

It does not own persistent event state or grant permissions. Tool authorization is enforced by Core API.

### RAG API
Owns document knowledge:
- authorized source registry and ingestion;
- parsing, chunking, metadata, document versions;
- sparse and dense indexes;
- hybrid retrieval, fusion, optional reranking;
- source excerpts, page citations, grounded answers and abstention.

It does not decide current event status or venue availability.

### Frontend
Owns interaction and presentation only. It cannot be the enforcement point for scheduling, permissions or status transitions.

The frontend has separate organizer and student views. The student event feed includes only events that an organizer explicitly published to that audience. Private planning records, commitments, evidence, calendar data, timetable data, attendance values, and registration-risk warnings never appear in organizer views.

## 4. Trust boundaries
- Browser → Core API: authenticated public application boundary.
- Core API → Agent/RAG: private service-to-service boundary.
- Agent → tools: allowlisted typed operations; no arbitrary shell/SQL/network tool.
- RAG document text → model: untrusted content. Text cannot override system/tool policy.
- Official confirmation: trusted only when actor/source authorization and evidence checks pass.
- Groq is an external generation boundary. Send only approved content and retain a deterministic local mock path for tests and demos.
- Student academic data: private boundary. The Core API returns academic-risk results only to the authenticated student and does not send calendar titles, timetable entries, attendance values, or risk details to organizers, Agent, or RAG.

## 4.1 Student registration-risk flow
1. An organizer publishes an event with a student audience and one registration mode: internal, external, or none.
2. A student lists published events and opens an event detail page.
3. Before registration or external redirect, the Core API evaluates the event interval against the student's seeded or connected academic-calendar events, timetable, and mock attendance snapshot.
4. Core returns private advisory warnings for direct exam conflicts, next-day exams, and class overlaps with attendance context.
5. The student chooses to continue or cancel. Warnings do not make an academic eligibility decision.
6. Internal registration creates a registration record. External mode records only that the student was redirected; it does not claim the external form was completed.

## 5. Event change flow
1. User submits proposed changes with the current event revision.
2. Core validates permissions and checks schedule constraints.
3. Dependency engine finds commitments/tasks tied to changed fields.
4. Core returns deterministic impacts and items needing revalidation.
5. Agent explains the impact and drafts follow-ups.
6. User reviews.
7. Core applies the authorized mutation transactionally, creates a revision and audit record, and marks affected commitments as needing revalidation where appropriate.

The agent must not apply a change based on stale event data. Mutations should include expected revision/version.

## 6. Scheduling invariants
- Intervals are timezone-aware and normalized to UTC for persistence.
- Campus display timezone is `Asia/Kolkata`.
- Event intervals use `[start, end)` semantics.
- Start must be strictly before end.
- Same-venue confirmed intervals may not overlap unless an explicitly authorized `VENUE_OVERLAP` override is recorded.
- The default campus-wide gap is 120 minutes between consecutive events; exactly 120 minutes passes. Core treats a violation as blocking unless an authorized administrator records a scoped `CAMPUS_GAP` override.
- The gap rule's institutional validity must be verified. Until then, describe it as a CampusCue planning rule, not official university policy.
- A `CAMPUS_GAP` override never implicitly overrides a `VENUE_OVERLAP` conflict and must retain the administrator, reason, timestamp, and evidence reference where applicable.
- Conflict validation must be repeated inside the write transaction.
- Empty event results never establish that a venue is available.

## 7. Source ingestion boundary

CampusCue has two distinct ingestion paths:

1. **Policy RAG path:** reviewed procedural documents, beginning with the OSA handbook, are parsed with page and section metadata and entered into the RAG corpus for evidence-cited answers.
2. **Structured catalog path:** published event pages, academic calendar HTML and ICS entries, facilities, ICTS services, support routes, and club records are normalized into PostgreSQL for product views and deterministic use.

Both paths use the registered source URL, collection and verification timestamps, content hash when available, parser version, extraction result, and freshness or review state. Neither path can establish live venue availability from an empty or public calendar. The structured path keeps `UNKNOWN`, tentative, and verified booking states separate.

The fetch layer follows source-specific access rules and rate limits. It does not bypass campus authentication. HTML and ICS parsers extract only the fields in `SOURCE_REGISTRY.md`; pages that are historical, undated, or campus-ambiguous require review before presentation as current operational information.

## 8. RAG pipeline
Authorized policy sources -> parse with page/section metadata -> structure-aware chunks -> SPLADE sparse retrieval + local dense retrieval -> RRF fusion -> optional reranking -> access-filtered context selection -> Groq grounded answer -> citations and abstention flag.

Suggested first implementation:
- SPLADE for sparse retrieval.
- Local embeddings stored in `pgvector` for dense retrieval.
- RRF for fusion.
- Cross-encoder reranking only after a baseline is measured.
- A reviewed 30–50-question evaluation set.

## 9. Deployment
Docker Compose can run:
- `web` on host port 3000;
- `core-api` on 8000;
- `agent-api` on 8001;
- `rag-api` on 8002;
- `postgres` on 5432.

For development, ports 8001 and 8002 may be published to localhost for direct testing. In integrated or production environments, keep Agent and RAG on a private network. Never expose administrative ingestion or internal tools without authentication.

## 10. Failure behavior
- Agent unavailable: core event CRUD and scheduling remain usable; policy/agent features show unavailable state.
- RAG unavailable: agent must not invent policy answers; return an explicit dependency error or ask the user to retry.
- LLM unavailable: deterministic APIs still work; retrieval-only search can still work if embedding/search dependencies are available.
- Missing/unclear source: RAG returns insufficient evidence.
- Structured-source failure: retain the last successful source timestamp, mark the catalog data stale or unavailable, and never infer availability from the failure.
- Conflict checker unavailable: do not confirm or commit a schedule mutation that requires validation.
- Stale revision: reject mutation with a conflict response and require refresh/review.
- Unknown venue availability: present as unknown, not free.
- Academic data unavailable: registration remains possible and the student sees that no academic-risk check could be completed.

## 11. Observability
Propagate `request_id`/correlation ID across Core, Agent and RAG. Log request metadata, tool name, latency, outcome, model/index version and error category. Do not log secrets, private conversation exports, full sensitive document bodies, or unrestricted user prompts by default.
