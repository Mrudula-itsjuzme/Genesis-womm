# CampusCue Implementation Plan

**Status:** Planning  
**Pilot:** Amrita Vishwa Vidyapeetham, Coimbatore  
**Purpose:** Master roadmap and execution index for humans and coding agents  
**Last updated:** 2026-10-10

## 1. Product definition

CampusCue is an AI-assisted event operations workspace for university clubs. It helps organizers plan before approvals arrive, discover verified campus resources and procedures, track requests and commitments, identify schedule conflicts, understand downstream change impact, prepare evidence-based reports, and publish events for student discovery and registration.

CampusCue is **not** an official venue-booking portal, a replacement for Student Affairs, or a generic club directory. The application must never imply that a venue is available or an event is officially approved unless an authorized source confirms it.

### Product outcome

Make the parts of event operations that clubs can prepare, coordinate, and verify easier, while accurately representing what remains institutionally unconfirmed.

### Primary demo

1. INIT creates a tentative AI Hackathon proposal for a date/time and preferred hall.
2. CampusCue finds a conflicting tentative event and explains the overlap.
3. The organizer explores sourced resource details and receives an OSA answer with page citations.
4. The organizer records a submitted venue request and an ICTS acknowledgment as separate commitments.
5. The event's venue or time changes.
6. CampusCue identifies affected tasks and commitments, flags items requiring revalidation, and drafts follow-ups.
7. CampusCue creates an editable event report from verified fields and highlights missing information.
8. A student opens the published event, receives private mock academic-risk warnings, and registers internally or continues to an external registration page.

All demo events and statuses must be explicitly labeled synthetic.

## 2. Non-negotiable principles

1. **Operational truth is deterministic.** Database state, authorization rules, scheduling constraints, and explicit evidence determine operational facts.
2. **The LLM is not an authority.** It may interpret requests, retrieve evidence, explain consequences, and draft actions. It cannot grant approvals or bypass constraints.
3. **Tentative intent is not a booking.** A proposal, submitted request, acknowledgment, conditional confirmation, and official confirmation are different states.
4. **Unknown means unknown.** An empty calendar or missing feed does not mean a venue is free.
5. **Every official confirmation is traceable.** Preserve source/evidence reference, authority, verification time, and audit history.
6. **Human review for consequential actions.** No automatic email sending, approval revocation, official status promotion, or administrator override in the MVP.
7. **Source-grounded knowledge.** RAG answers include citations and excerpts, distinguish documented policy from suggestions, and abstain when evidence is insufficient.
8. **Privacy by design.** Do not ingest private organizer-group exports, private WhatsApp conversations, personal participant data, or sponsor information into public or general-purpose RAG indexes.
9. **Parallel work requires contracts.** Teams build against versioned schemas and mocks rather than waiting for full integration.
10. **Every claim is testable.** Favor measurable acceptance criteria over claims of reducing approval time without evidence.

## 3. Scope

### MVP must-have
- Event proposal creation and retrieval.
- Tentative event calendar/list and overlap detection.
- Deterministic scheduling rules, including the configurable two-hour gap policy.
- Resource catalog with source, verification date, responsible office, restrictions, and availability state.
- RAG ingestion and hybrid dense + sparse retrieval with page citations.
- Separate, allowlisted source ingestion: reviewed policy/procedure documents go to RAG; events, calendars, facilities, services, and clubs go to PostgreSQL with provenance and freshness state.
- Agent service with bounded typed tools.
- Commitment status and evidence references.
- One working venue/time change-impact scenario.
- Editable event summary with missing fields visibly flagged.
- Role-based access for organizers and authorized administrators.
- Published student event feed with visibility controls.
- Internal registration and organizer-configured external registration redirect.
- Student registration-risk check using seeded timetable/exam data and a mock attendance provider. A read-only Google Calendar connection may replace seeded exam data when configured.
- Synthetic demo seed data, tests, Docker-based local development, and API documentation.

### If time permits
- Volunteer shift acknowledgment and gap alerts.
- Judging score-sheet completeness.
- Sponsor obligation checklist.
- Monthly report compilation.
- Retrieval/reranking evaluation dashboard.

### Later, only with university permission/integration
- Live venue availability or official booking integration.
- Authorized campus calendar sync.
- Institution-verified approval status.
- Approved institutional attendance API integration.
- Production Google OAuth verification and incremental calendar synchronization.
- Search over approved, sanitized prior event playbooks.
- Automated notification delivery.

### Explicitly out of scope for MVP
- Replacing Student Affairs or official booking systems.
- Claiming a tentative event reserves a hall.
- Automatic official approval or approval revocation.
- Automatic outbound emails/messages.
- Public exposure of internal event conversations or financial details.
- Organizer access to a student's calendar events, timetable, attendance values, or private registration-risk warnings.
- A large distributed microservice ecosystem beyond the three independently deployable application services and supporting database.

## 4. System architecture

### Services

| Service | Owns | Must not own |
|---|---|---|
| Core API | AuthZ, operational database, event/resource APIs, scheduling, state transitions, audit history, dependencies, reports' verified input data | LLM reasoning or policy corpus as operational authority |
| Agent API | Conversation turn, request interpretation, bounded tool orchestration, explanations, action drafts | Direct database writes, scheduling truth, authorization decisions |
| RAG API | Document ingestion, parsing, chunk metadata, sparse/dense indexes, retrieval, citations, grounded answers | Event status, venue availability, official approval decisions |
| Web frontend | User interaction, visualization, editable drafts, confirmation prompts | Authoritative conflict enforcement or permission checks |

### Recommended stack
- Frontend: Next.js + Tailwind CSS (selected).
- Core API: Python + FastAPI for MVP simplicity.
- Agent API: Python + FastAPI.
- RAG API: Python + FastAPI.
- Database: PostgreSQL with `pgvector` for locally generated dense embeddings.
- LLM provider: Groq for agent and grounded-answer generation. Keep a deterministic mock provider for tests and demo fallback.
- Sparse retrieval: SPLADE. Fuse SPLADE and local dense-embedding results with Reciprocal Rank Fusion.
- Migrations: Alembic if using SQLAlchemy.
- Containers: Docker and Docker Compose.
- Contracts: OpenAPI plus Pydantic request/response schemas; keep contract fixtures in `contracts/`.
- Testing: pytest, API contract tests, database integration tests, retrieval evaluation scripts.
- Observability: structured logs with request/correlation IDs; never log secrets or private document contents by default.

### Local development ports
- Web: `3000`
- Core API: `8000`
- Agent API: `8001`
- RAG API: `8002`
- PostgreSQL: `5432`

Expose Agent/RAG ports to host only when needed for development. In an integrated deployment, keep them on a private network behind the Core API. Ports are defaults, not immutable requirements.

### Request paths
- Ordinary CRUD and scheduling: Web → Core API.
- Policy question: Web → Core API → Agent API → RAG API; agent returns citations and evidence IDs.
- Change impact: Web → Core API stages/checks change → deterministic dependency analysis → Agent explains results and drafts follow-ups → user reviews → Core API applies authorized change and audits it.
- RAG evaluation: test harness → RAG API directly.
- Agent evaluation: test harness → Agent API with mocked Core/RAG clients.

## 5. Scheduling policy and conflict semantics

The product enforces a **campus-wide minimum two-hour gap between consecutive events** by default, even across different venues, plus a venue-level no-overlap rule. The gap is a CampusCue planning rule until institutional validation establishes otherwise. An authorized administrator may record a scoped `CAMPUS_GAP` override for a justified exception; all other users receive the conflict and cannot bypass it.

### Interval semantics
Use half-open intervals `[start_at, end_at)`. Require `start_at < end_at`. Normalize instants to UTC for persistence and retain the campus timezone (`Asia/Kolkata`) for display/input interpretation.

For events A and B, the temporal-gap rule is satisfied if:
- `end_A + 120 minutes <= start_B`, or
- `end_B + 120 minutes <= start_A`.

Exactly 120 minutes is allowed. A 119-minute gap is a violation. Overlapping intervals are violations.

### Conflict classes
- `VENUE_OVERLAP`: overlapping event intervals at the same venue. Hard conflict unless an authorized venue-overlap override exists.
- `CAMPUS_GAP_VIOLATION`: less than two hours between consecutive events under the default campus-wide planning rule. Blocking unless an authorized `CAMPUS_GAP` override exists.
- `TENTATIVE_OVERLAP`: conflicting proposal/interest that is not a confirmed reservation; normally a warning, not a booking claim.
- `DEPENDENCY_CONFLICT`: a shared support resource, audience, organizer, equipment, volunteer group, or other dependency is incompatible.
- `UNKNOWN_AVAILABILITY`: no authoritative source is available to establish real-time venue availability.

### Status handling
Suggested event lifecycle: `DRAFT → PROPOSED → SUBMITTED → CONFIRMED → COMPLETED`, with explicit `REJECTED` and `CANCELLED` terminal/alternative states as needed. Do not conflate event lifecycle with individual commitment statuses.

Suggested commitment lifecycle: `DRAFT → REQUESTED → ACKNOWLEDGED → CONDITIONALLY_CONFIRMED → CONFIRMED → NEEDS_REVALIDATION → CLOSED`. Transitions must be validated by Core API. Acknowledgment is not confirmation.

### Overrides
Overrides are explicit, scoped, authorized and audited. Only an authorized administrator may create one. Model at least:
- `override_scope`: `CAMPUS_GAP` or `VENUE_OVERLAP`
- affected event IDs / interval
- reason
- authorized actor
- creation timestamp
- evidence reference where required

A campus-gap override must not silently permit a venue double-booking. An override bypasses only the named constraint. The AI agent cannot create or authorize an override. The core authorization layer must reject unauthorized attempts and audit the approved exception.

### Concurrency
Conflict checks must run in the same transaction as the write that creates or confirms a booking. A prior frontend/agent check is advisory and cannot guarantee the write remains valid. Use PostgreSQL range queries and, where appropriate, an exclusion constraint for confirmed same-venue overlaps. The campus-wide gap check requires transaction-safe enforcement/locking to prevent concurrent conflicting writes.

## 6. Agent service design

### Responsibilities
- Parse organizer requests into structured event intent.
- Ask for missing critical fields instead of guessing.
- Call Core API tools to read operational facts and run conflict checks.
- Call RAG for relevant, cited policy evidence.
- Explain conflicts, uncertainty, and potential downstream impact.
- Draft checklists, follow-ups, and report content.
- Return structured actions and approval requirements.

### Initial tools
- `check_event_conflicts`
- `create_event_draft`
- `get_event_details`
- `get_event_timeline`
- `request_event_change`
- `get_change_impact`
- `get_resource_details`
- `search_campus_policy`
- `get_event_checklist`
- `record_commitment` (only where actor is authorized)
- `create_followup_draft`
- `generate_event_report`

Do not expose an unrestricted `book_event` tool. Official confirmation is a distinct authorized operation that requires validated evidence and permissions. In the MVP, prefer proposal creation and request/acknowledgment tracking.

### Agent controls
- Typed input/output schemas and tool argument validation.
- Maximum tool-call count and execution timeout.
- Tool allowlist; no arbitrary SQL, shell, or unrestricted HTTP tools.
- Per-tool authorization in Core API, not merely prompt instructions.
- Idempotency keys for mutation tools.
- Explicit human review for consequential operations.
- Structured trace of tool calls and outcomes.
- Never report a mutation as successful until the tool returns success.
- Treat retrieved documents and user-provided content as untrusted data, not instructions to override agent policy.
- Tests for prompt injection, missing evidence, denied permissions, failed tools, retries, and stale event revisions.

### Initial Agent endpoints
- `POST /v1/agent/chat`
- `POST /v1/agent/plan-event`
- `POST /v1/agent/analyze-change`
- `GET /health`
- `GET /ready`

## 7. RAG service design

### Ingestion
- Allowlist authorized document sources.
- Parse PDF/HTML/DOCX with page/section metadata preserved.
- Store source URL, title, document ID/version, content hash, page range, section, access level, ingestion timestamp, and verification timestamp.
- Chunk along headings/clauses first; start testing around 400–700 tokens with modest overlap.
- Track parse failures and document supersession.
- Do not ingest private organizer exports or unapproved sensitive material.
- Use `SOURCE_REGISTRY.md` as the initial Amrita Coimbatore allowlist. The OSA handbook is the first policy document; the Student Affairs page requires content review before RAG activation.
- Do not send event pages, calendar feeds, facility directories, ICTS pages, or club pages into the policy RAG corpus merely because they are scraped. Extract their operational fields into PostgreSQL through source-specific HTML or ICS parsers.
- A public event calendar is discovery context, not a live venue-availability or booking feed. Retain `UNKNOWN` availability unless authorized evidence establishes otherwise.

### Retrieval pipeline
1. Normalize query without destroying exact identifiers.
2. Apply access-level filters.
3. Retrieve sparse candidates using SPLADE.
4. Retrieve dense candidates using local embeddings and `pgvector`.
5. Fuse rankings with Reciprocal Rank Fusion (RRF).
6. Optionally rerank top candidates with a cross-encoder.
7. Select context under a token budget, preserving source metadata.
8. Generate answer only from retrieved evidence.
9. Return source excerpts, page citations, evidence IDs, and an insufficiency signal.

Initial tuning ranges are hypotheses, not requirements: 20–30 candidates from each retriever, fuse, rerank the top 10–20, and supply the best few evidence chunks to generation. Evaluate rather than assuming these settings are optimal.

### RAG endpoints
- `POST /v1/retrieval/search`
- `POST /v1/knowledge/answer`
- `POST /v1/knowledge/ingest` (admin-only)
- `GET /v1/knowledge/documents`
- `GET /health`
- `GET /ready`

### RAG evaluation
Build 30–50 manually reviewed questions covering exact lookup, paraphrases, multi-part event procedures, ambiguous cases, and unanswerable questions. Compare sparse-only, dense-only, and hybrid:
- Recall@k
- MRR and/or nDCG
- Citation correctness
- Answer faithfulness
- Abstention quality
- Latency and resource use

A similarity score alone is not proof of answer confidence. Citation metadata must come from the index, never be invented by the generator.

## 8. Core API design

### Responsibilities
- Authentication and role-based authorization.
- Clubs, memberships, resources, events, revisions, commitments, evidence, tasks, dependencies, overrides.
- Deterministic conflict engine and transactional enforcement.
- Status transition validation and audit events.
- API calls to Agent/RAG.
- Verified-data assembly for reports.
- Idempotency, validation, error handling and request tracing.

### Initial domain entities
- `clubs`
- `memberships`
- `resources`
- `events`
- `event_revisions`
- `event_commitments`
- `evidence_records`
- `event_dependencies`
- `tasks`
- `schedule_overrides`
- `audit_events`
- `event_publications`
- `event_registrations`
- `student_timetables`
- `student_attendance_snapshots`
- `student_academic_calendar_events`
- `documents` / `document_sources` if the Core API needs to display RAG catalog metadata; do not duplicate the RAG chunk index.

### Initial Core API routes
- `POST /api/v1/events`
- `GET /api/v1/events`
- `GET /api/v1/events/{event_id}`
- `POST /api/v1/events/{event_id}/conflict-check`
- `POST /api/v1/events/{event_id}/change-proposals`
- `GET /api/v1/events/{event_id}/impact`
- `GET /api/v1/events/{event_id}/timeline`
- `GET /api/v1/resources`
- `GET /api/v1/resources/{resource_id}`
- `POST /api/v1/agent/chat`
- `POST /api/v1/reports/event-summary`
- `GET /api/v1/student/events`
- `POST /api/v1/events/{event_id}/registration-risk-check`
- `POST /api/v1/events/{event_id}/registrations`
- `GET /health`
- `GET /ready`

Exact routes may evolve during contract design; update the OpenAPI specs and contracts in the same change.

## 9. Data model and evidence principles

- Store event instants as timezone-aware timestamps; display in `Asia/Kolkata`.
- Event revisions capture previous and new values, actor, timestamp, and change reason.
- Commitments are independent records, because ICTS may acknowledge a request while venue or equipment support remains unconfirmed.
- Evidence records include type, URI/reference, issuer/source, captured time, verified-by, and visibility/access control.
- Keep private contacts, financial data, internal conversations, and participant data restricted by default.
- Report fields should carry provenance/verification state where useful.
- Unknown availability must be represented explicitly, never inferred from no matching event rows.

## 10. API contract conventions

- JSON over HTTP; OpenAPI generated from the service.
- Prefix public APIs with `/api/v1`; internal service APIs may use `/v1`.
- Use stable UUIDs for persistent entities.
- Timestamps must be ISO 8601 with timezone; reject ambiguous local timestamps unless a campus timezone is explicitly applied.
- Errors use a consistent envelope: `code`, `message`, `details`, `request_id`.
- Mutation requests accept `Idempotency-Key` where duplicate submission is harmful.
- Include `event_version`/revision in change requests to detect stale edits.
- Return conflict objects with stable `type`, `severity`, `event_ids`, `time_window`, `message`, and `override_required`.
- RAG citations use stable `evidence_id`, `document_id`, `title`, `page_start`, `page_end`, `source_url`, and exact excerpt.
- No internal database schema is exposed directly to the frontend.

## 11. Security, privacy, and operational safety

- Authenticate all non-public operations.
- Authorize every resource read and mutation server-side.
- Separate organizer, club admin, campus admin, and service identities.
- Agent and RAG service-to-service requests use internal credentials in non-local deployments.
- Never put secrets in source control or example `.env` files.
- Use least privilege for document ingestion and administrative overrides.
- Enforce access filtering before RAG retrieval, not only in generated prose.
- Treat indexed content as untrusted; retrieved text cannot change tool permissions or system instructions.
- Log actor, action, entity, outcome, timestamp, request ID and override reason. Avoid logging sensitive body contents.
- Keep synthetic and real pilot data clearly separated.
- Treat attendance, timetable, calendar, and registration-risk data as student-private records. The Core API returns only the current student's warnings.
- Do not claim compliance or institutional approval that has not been established.

## 12. Testing strategy

### Core API
- Unit tests for interval overlap, exactly-two-hour boundary, 119-minute gap, event exclusions, cancellations and override scope.
- Integration tests for transactions, concurrent conflicting requests, same-venue exclusion, permissions and stale revisions.
- Contract tests against documented request/response schemas.
- Tests proving an empty calendar does not imply availability.

### Agent
- Tool-selection tests using deterministic fixtures.
- No mutation when required fields are missing.
- No claim of booking/confirmation after a failed tool call.
- No direct database access or unauthorized override.
- Tool timeout/retry/idempotency tests.
- Prompt-injection tests against user content and retrieved excerpts.
- Structured response validation.

### RAG
- Parsing and page metadata tests.
- Retrieval evaluation for sparse, dense and hybrid.
- Citation-to-excerpt integrity tests.
- Unanswerable-question abstention tests.
- Document version/supersession and access-filter tests.

### End-to-end
- Tentative overlap warning.
- Confirmed same-venue conflict.
- Cross-venue campus-gap conflict.
- Authorized campus-gap override does not bypass venue constraint.
- Venue change marks affected commitments for revalidation.
- Event report shows missing attendance/photos/speaker data rather than fabricating it.
- A student can see only published events and cannot see organizer-only planning records.
- An event overlapping a seeded class with low mock attendance returns a private warning without blocking registration.
- An external registration flow records a redirect, not a completed registration.

## 13. Workstreams and integration

### Workstream A: Core API and scheduling
Owns database migrations, event/resource APIs, conflict engine, permissions, revisions, commitments, overrides and contract fixtures.

### Workstream B: Agent API
Owns LLM abstraction, orchestration, tool schemas, mock clients, traces, safety tests, and structured action drafts.

### Workstream C: RAG API
Owns ingestion, sparse/dense indexes, hybrid fusion, reranking experiments, citations, source versioning and evaluation.

### Workstream D: Frontend
Owns organizer event intake, calendar/list, conflict explanation, resource explorer, policy assistant, impact view, report editor, and the student event discovery and registration experience. It starts against mocks.

### Integration rule
All workstreams begin with service skeletons and shared contracts. Each team must have a local mock-based test path. Integrate a vertical slice early; do not wait until all feature branches are “finished.”

## 14. Milestones

1. **M0: Decisions and contracts** — confirm scheduling semantics, status model, role model, service contracts and selected frontend framework.
2. **M1: Runnable skeletons** — all services start independently; health endpoints and OpenAPI specs exist; Compose runs.
3. **M2: Core scheduling** — create event proposals, conflicts and scoped override tests.
4. **M3: RAG baseline** — ingestion, hybrid retrieval, citations, evaluation set.
5. **M4: Agent baseline** — bounded tools and mock integration, then real Core/RAG clients.
6. **M5: Change-impact vertical slice** — change event details, identify dependencies, draft follow-ups.
7. **M6: Student registration vertical slice** — publish an event, show private mock academic-risk checks, and register or redirect.
8. **M7: Report and UI polish** — editable report and explicit missing fields.
9. **M8: Demo hardening** — end-to-end tests, synthetic seed data, setup guide, known limitations.

Do not assign dates until the hackathon schedule and team availability are confirmed.

### Integration progress — 2026-10-11

The [frontend/backend integration](docs/superpowers/plans/2026-10-11-full-frontend-backend-integration.md) connects the existing Next.js app to Core for sessions, calendar/details, tentative drafts/conflict advice, venue provenance, PDF proposals and human-reviewed Agent actions. M7 has editable local reports with explicit missing facts. M8 has synthetic seeds, setup documentation, 11 browser regressions and one live database/storage/gateway smoke test.

M5 now includes persisted schedule-change proposals, deterministic field dependency impact and atomic revalidation through Core and the Changes page (Plan 08). Organizers stage changes; club/campus administrators apply them after review. Commitment timeline/evidence verification and drafted follow-ups remain pending. Server-backed reporting, real RAG model/index integration and broader M8 hardening remain pending. The entire roadmap is not marked complete. See [HANDOFF.md](HANDOFF.md) for commits, commands, results and limits.

## 15. Definition of done

A feature is done only when:
- The owning service has documented API/schema changes.
- Tests cover normal, boundary, error and permission paths as applicable.
- The service works independently with documented configuration.
- Logs and errors are actionable and do not expose secrets.
- The UI distinguishes confirmed facts from tentative claims.
- The implementation plan's acceptance criteria are met.
- Relevant docs and contract fixtures are updated.
- The feature is demonstrated in the integrated flow or explicitly marked not integrated.

## 16. Open decisions

Resolve before implementing the corresponding feature:
1. Confirm whether the two-hour gap is a product-wide scheduling rule, a verified campus policy, or a configurable planning warning. Default implementation assumption: campus-wide planning rule, clearly labeled as unverified until confirmed.
2. Define which event states block new proposals versus produce warnings.
3. Define roles and who may record an official confirmation.
4. Select React/Vite versus Next.js and Core API language.
5. Select and benchmark the local embedding model and SPLADE checkpoint against campus terminology. Groq is the selected generation provider; retain the mock provider for tests and fallback.
6. Confirm allowed source documents, resource data, and document access classes.
7. Confirm official report formats and resource verification workflow.
8. Decide whether tentative cross-club event visibility is opt-in and which fields are public to participating clubs.
9. Define the student event-publication audience, registration fields, and organizer responsibilities for external registration links.
10. Confirm the academic-risk warning language and whether any approved attendance threshold exists. Until then, attendance warnings remain advisory.

## 17. Documentation map

- `PROJECT.md`: stable product scope, users, terminology, constraints and success criteria.
- `PLAN.md`: master roadmap and milestone status.
- `CONTEXT_ARCHITECTURE.md`: service boundaries, data flows, trust boundaries and deployment.
- `AGENTS.md`: instructions for coding agents and orchestration rules.
- `Implementation_Plans/`: executable, ordered plans required before feature implementation.
- `contracts/`: API schemas, sample payloads and error conventions.
- `prompts/`: reusable coding-agent task prompts.
- `README.md`: developer setup and local commands.
- `HANDOFF.md` and any existing Git protocol: preserve existing versions; do not replace or silently rewrite them.
