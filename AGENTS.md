# AGENTS.md: CampusCue Zero-Context Operational Playbook

> **Mandatory boot rule:** Any AI coding agent or developer entering this repository without prior conversation context must read this document and the project context documents before modifying files.
>
> This file defines the operating protocol for CampusCue. Product requirements and architectural decisions live in the project documents; this file defines how implementation work is planned, executed, verified, and handed off.

## Repository and Git invariants

CampusCue enforces strict, incremental version-control discipline. Rather than accumulating monolithic, multi-file diffs to commit at the end of a session, create small, verified, incremental Git commits as each cohesive unit of work is completed.

### 1. Incremental commit cadence and batch sizing

- **Commit cadence:** Create an atomic Git commit every 2–3 related files that complete a logical, cohesive feature slice or testable increment.
- **Do not hoard changes:** Never defer all commits to the end of a task or session. Large diffs (>4 files across unrelated modules or cross-cutting boundaries) must be split into incremental commits.
- **Cohesive 2–3 file pairings:**
  - *Data layer:* Domain model + migration script (e.g., `apps/core/models/event.py` + `apps/core/migrations/0002_event_schema.py`)
  - *Domain logic & testing:* Service implementation + unit test suite (e.g., `apps/core/services/scheduling.py` + `tests/core/test_scheduling.py`)
  - *API & specification:* Route handler + API contract update (e.g., `apps/core/api/events.py` + `contracts/events.yaml`)
  - *Client & integration:* Tool client wrapper + mock/client test (e.g., `apps/agent/tools/core_client.py` + `tests/agent/test_core_client.py`)
  - *Frontend:* UI component + component test/fixture (e.g., `frontend/src/components/ConflictCard.tsx` + `frontend/src/components/ConflictCard.test.tsx`)
  - *Pipeline:* Retrieval component + evaluation fixture (e.g., `apps/rag/retrieval/fusion.py` + `tests/rag/test_fusion.py`)
- **Verification prerequisite:** Every commit must represent a working, valid state. Run relevant localized tests, formatters, or type-checks for the staged slice before committing. Never commit broken, unparseable, or non-compiling intermediate code.

### 2. Atomic staging rules

- **Explicit file staging only:** Always specify exact file paths explicitly:
  ```bash
  git add apps/core/services/scheduling.py tests/core/test_scheduling.py
  ```
- **Strictly prohibited staging commands:**
  - NEVER use `git add .`
  - NEVER use `git add -A` or `git add --all`
  - NEVER use `git add -u` across the repository root
  - NEVER use `git commit -a` or `git commit -am "..."`
- Staging wildcards or blind additions risk sweeping in untracked operational notes, secrets, build artifacts, or concurrent user modifications.

### 3. Pre-staging and post-staging inspection protocol

Follow this exact command flow for every commit:

1. **Inspect repository state:**
   ```bash
   git status --short
   git diff <file1> <file2>
   ```
2. **Stage explicit targets:**
   ```bash
   git add <file1> <file2>
   ```
3. **Verify the staged diff before committing:**
   ```bash
   git diff --cached --stat
   git diff --cached
   ```
   Confirm that *only* the intended 2–3 files are staged, diff hunks are minimal and clean, and no debug statements or unintended edits are present.

### 4. Commit message standards (Conventional Commits)

All commit messages must strictly adhere to the Conventional Commits specification:

```text
<type>(<scope>): <imperative summary>

[optional body with rationale and implementation plan reference]
```

- **Allowed types:**
  - `feat`: New feature, endpoint, data model, tool, or UI component.
  - `fix`: Bug fix, constraint correction, or error handling repair.
  - `test`: Adding, expanding, or refactoring unit, contract, or integration tests.
  - `refactor`: Internal code restructuring with zero behavioral or contract changes.
  - `docs`: Documentation updates (`PLAN.md`, `CONTEXT_ARCHITECTURE.md`, guides).
  - `chore`: Dependency updates, tooling configuration, or build scripts.
- **Allowed scopes:**
  - `core`: Core API service, PostgreSQL models, migrations, deterministic scheduler.
  - `agent`: Agent API service, LLM orchestration, tool definitions, prompts.
  - `rag`: RAG API service, document ingestion, embeddings, search fusion.
  - `frontend`: React application, components, state management, UI styling.
  - `contracts`: Shared schemas, OpenAPI specifications under `contracts/`.
  - `infra`: Docker Compose, database containers, environment configuration.
- **Message syntax rules:**
  - Use the **imperative, present tense mood** ("add", "fix", "enforce", "refactor"; not "added", "fixing", "enforces").
  - Lowercase summary line with no trailing period.
  - Keep the summary line concise (under 72 characters).
  - If executing an active implementation plan, include a reference in the commit body (e.g., `Refs: Step 2.1 in Implementation_Plans/01_core_scheduling.md`).
- **Examples:**
  - `feat(core): implement half-open interval conflict check for venue bookings`
  - `test(core): add unit tests for 120-minute campus gap boundary conditions`
  - `fix(agent): handle missing venue id in tool argument validation`
  - `feat(rag): add reciprocal rank fusion for sparse and dense retrieval`
  - `docs(contracts): define conflict override schemas for venue overlaps`

### 5. Git state and history invariants

- **Preserve existing user changes:** Never overwrite, revert, discard, or overwrite uncommitted user changes. Always inspect `git status` and `git diff` before touching any file.
- **Branch hygiene:** Work exclusively on designated feature or task branches. Never commit directly to protected or release branches (`main`, `master`, `prod`) unless instructed.
- **No destructive history manipulation:**
  - NEVER execute `git push --force` or `git push --force-with-lease` on shared or upstream branches.
  - NEVER rewrite published history via rebase or reset on shared branches.
  - NEVER run destructive reset commands (`git reset --hard`, `git clean -fd`) without explicit user instruction.

### 6. Protected files and sensitive asset exclusion

- **Protected operational files:** Never stage or commit `AGENTS.md` or `HANDOFF.md` unless the user explicitly commands it. Do not add either file to `.gitignore`.
- **Secrets and environment variables:** Never commit `.env`, `.env.*`, API tokens, private keys, database passwords, or personal credentials. Only committed templates like `.env.example` with scrubbed dummy placeholders are allowed.
- **Ephemeral artifacts:** Never commit scratch scripts, temporary files (`scratch/`), debug transcripts, test dumps, coverage artifacts, or editor config directories (`.idea/`, `.vscode/`).
- **Tracked project documents:** `PLAN.md`, `PROJECT.md`, `CONTEXT_ARCHITECTURE.md`, `contracts/`, and approved plans under `Implementation_Plans/` are tracked assets and should be committed whenever updated to reflect architectural or operational progress.

### 7. Local commit rollback and safety procedures

If a local commit contains an error or needs adjustment *before* pushing to remote:

- **Unstaging files before committing:**
  ```bash
  git restore --staged <file>
  ```
- **Amending the immediate last local commit:**
  If the commit is purely local and unpushed, and you need to fix a typo or add a missed companion file in the same 2–3 file slice:
  ```bash
  git add <missed-file>
  git commit --amend --no-edit
  ```
- **Stepping back a local commit cleanly:**
  If a commit needs to be split or redesigned, use soft reset to move `HEAD` back while preserving all changes intact in the staging area / working directory:
  ```bash
  git reset --soft HEAD~1
  ```
  Then restage the files in properly sized 2–3 file atomic batches.
- **Strict safety rule:** NEVER use `git reset --hard` to undo a commit unless explicitly ordered by the user, as it permanently discards uncommitted work in the working tree.

---

# 1. Thirty-second orientation

| Dimension | CampusCue ground truth |
|---|---|
| Product | AI-assisted event operations workspace for university clubs |
| Pilot | Amrita Vishwa Vidyapeetham, Coimbatore |
| Core value | Plan before approvals arrive, discover campus resources and procedures, track commitments, identify conflicts and downstream change impact, and prepare reports |
| Core API | Authoritative operational state, authorization, event lifecycle, deterministic scheduling and audit history |
| Agent API | Bounded LLM/tool orchestration, natural-language interpretation, explanations and action drafts |
| RAG API | Approved-document ingestion, hybrid dense/sparse retrieval, citations and evidence-grounded answers |
| Frontend | React-based application; use the framework selected in `PLAN.md` and existing repository configuration |
| Database | PostgreSQL; `pgvector` and PostgreSQL full-text search are the initial RAG baseline unless the project explicitly chooses otherwise |
| Local development | Docker Compose for services and dependencies; individual services must remain independently testable |
| API contracts | OpenAPI and typed request/response schemas under `contracts/` |
| Master roadmap | `PLAN.md` |
| Product definition | `PROJECT.md` |
| Architecture | `CONTEXT_ARCHITECTURE.md` |
| Detailed plans | `Implementation_Plans/` |
| Current handoff | `HANDOFF.md`, if the repository uses it; preserve its existing format and update it when required by repository policy |

## Product truth that must never be violated

- A tentative event proposal is **not** a venue booking.
- Submitted is not acknowledged; acknowledged is not official confirmation.
- An empty calendar does not prove a venue is available.
- The LLM does not own scheduling truth, authorization, or official status.
- The two-hour campus-wide gap is a configurable CampusCue planning rule until its institutional validity is verified.
- A campus-gap override does not automatically override a venue-overlap conflict.
- Official confirmations require an authorized actor/source and suitable evidence.
- AI-generated reports are editable drafts. Do not invent attendance, photos, speakers, reimbursements, acknowledgments, or approvals.
- Do not ingest private organizer-group exports or private conversations into a public or general-purpose RAG index.
- Use synthetic and clearly labeled data for demos unless approved real pilot data is explicitly available.

---

# 2. Zero-context boot sequence

Follow this sequence at the start of a new task.

## Step 1: Read the context documents

Read, in order:

1. `AGENTS.md` (this file).
2. `HANDOFF.md`, if present.
3. `PROJECT.md`.
4. `PLAN.md`.
5. `CONTEXT_ARCHITECTURE.md`.
6. The relevant contract files under `contracts/`.
7. The relevant plan under `Implementation_Plans/`.

If one of the referenced files does not exist, do not assume its contents. Inspect the repository and report the missing document when relevant.

## Step 2: Inspect repository state

Run and inspect:

```bash
git status --short
git diff --stat
git diff
```

Do not revert user changes. Inspect the repository tree, package manifests, service entrypoints, migrations, Compose configuration, and test commands before deciding how to implement the task.

## Step 3: Establish a baseline

Run the narrowest useful baseline checks for the affected service before changing code. Use commands that actually exist in its manifest or Makefile.

Potential checks, only when configured:

```bash
# Python service
pytest
ruff check .
mypy .

# Frontend
npm run lint
npm run build
npx tsc --noEmit

# Docker Compose
docker compose config
docker compose ps
```

Do not blindly run every example command. If the repository uses different tools, use its real commands. Record pre-existing failures separately from regressions introduced by the task.

## Step 4: Identify the active objective

- Read the task and identify the owning service.
- Find the corresponding implementation plan.
- Identify contracts, schema migrations, and dependent workstreams.
- If a non-trivial task has no implementation plan, write one before implementation.
- Identify assumptions and unresolved product decisions. Do not silently turn an assumption into official university policy.

## Step 5: Execute a small, verifiable change

Work in tight, disciplined vertical slices using an incremental **Red-Green-Verify-Commit inner loop**. Never write massive multi-component diffs or accumulate large uncommitted changes across the repository.

### 5.1 The 2–3 File Slicing Rule
Decompose every task into atomic units containing strictly **2 to 3 cohesive files**:
- **Pattern A (Test + Implementation):** 1 test file (e.g., `tests/unit/test_scheduling.py`) + 1 implementation file (e.g., `services/scheduling.py`).
- **Pattern B (Contract + Migration + Model):** 1 schema/contract file (e.g., `contracts/events.yaml`) + 1 migration script + 1 domain model.
- **Pattern C (UI Component + Fixture/Hook):** 1 React component + 1 custom hook or test fixture.

If an edit spans 4 or more files, stop and split the work into smaller sequential slices before continuing.

### 5.2 The Red-Green-Verify-Commit Inner Loop

```text
┌─────────────────────────────────────────────────────────────┐
│                      THE INNER LOOP                         │
│                                                             │
│  1. SLICE  ───► Select discrete 2–3 file boundary           │
│       │                                                     │
│       ▼                                                     │
│  2. RED    ───► Write targeted test & verify failure        │
│       │                                                     │
│       ▼                                                     │
│  3. GREEN  ───► Implement minimal production code           │
│       │                                                     │
│       ▼                                                     │
│  4. VERIFY ───► Run narrow test & targeted linters          │
│       │                                                     │
│       ▼                                                     │
│  5. DIFF   ───► Inspect exact slice diff & hygiene check    │
│       │                                                     │
│       ▼                                                     │
│  6. COMMIT ───► Stage explicit files & commit slice         │
│       │                                                     │
│       ▼                                                     │
│  7. REPEAT ───► Advance to next 2–3 file slice              │
└─────────────────────────────────────────────────────────────┘
```

#### Detailed Phase Protocol

1. **Slice (Atomic Scope Definition):**
   - Identify the next discrete unit from the active implementation plan.
   - Bound modifications strictly to the chosen 2–3 files. Do not touch unrelated files or refactor adjacent modules out of scope.

2. **RED (Failing Test First):**
   - Write or update tests in the slice test file that assert the required behavior, edge cases, or bugfix reproducer.
   - Run the specific test command. Confirm that it executes and fails for the expected reason (assertion failure or missing symbol, not syntax error or harness misconfiguration).

3. **GREEN (Minimal Implementation):**
   - Write the simplest code in the implementation file(s) that satisfies the failing test.
   - Avoid speculative generalizations, premature abstractions, or adding unrequested features.

4. **VERIFY (Narrow Verification):**
   - Re-run the targeted test to confirm it passes.
   - Run targeted static analysis (linter/typechecker) on the modified files to catch errors immediately.

5. **DIFF (Hygiene & Scope Inspection):**
   - Run `git diff` scoped specifically to the slice files.
   - Audit the diff line-by-line: eliminate debugging logs, temporary print statements, commented-out code, and unintended whitespace changes.
   - Confirm no sensitive credentials, secrets, or protected files (`AGENTS.md`, `HANDOFF.md`) are touched.

6. **COMMIT (Atomic Slice Commit):**
   - Commit the slice immediately once verified.
   - Stage files explicitly by path (`git add <file1> <file2>`). **Never run `git add .` or `git add -A`**.
   - Craft a concise, conventional commit message detailing the slice: `<type>(<scope>): <concise summary>` (e.g., `test(core): add two-hour campus gap boundary tests`, `feat(core): implement venue conflict interval check`).

7. **REPEAT:**
   - Proceed to the next 2–3 file slice until all subtasks in the implementation plan are completed.

### 5.3 Concrete Command Sequence for Step 5

Execute this exact command sequence for each slice:

```bash
# 1. Baseline status check before editing slice
git status --short

# 2. Write test, then confirm RED (failing test)
# Python example:
pytest tests/unit/test_conflict_engine.py -k "test_campus_gap_boundary" -v
# Frontend example:
npm test -- src/components/ConflictBanner.test.tsx

# 3. Implement minimal change in the 1-2 production files

# 4. Verify GREEN (passing test & targeted lint)
pytest tests/unit/test_conflict_engine.py -k "test_campus_gap_boundary" -v
ruff check src/services/conflict_engine.py tests/unit/test_conflict_engine.py
mypy src/services/conflict_engine.py

# 5. Inspect the exact slice diff
git diff --stat src/services/conflict_engine.py tests/unit/test_conflict_engine.py
git diff src/services/conflict_engine.py tests/unit/test_conflict_engine.py

# 6. Stage explicit files ONLY (never use 'git add .')
git add src/services/conflict_engine.py tests/unit/test_conflict_engine.py
git status --short

# 7. Commit the atomic slice
git commit -m "feat(core): enforce two-hour campus-wide gap in conflict engine"

# 8. Verify recorded commit
git log -1 --stat
```

---

## Step 6: Close the task accurately

Task closure is an explicit quality gate. Complete every item in the closure protocol before reporting completion.

### 6.1 Incremental Slice Audit
- Confirm that every planned 2–3 file slice was implemented, verified, and committed.
- Check `git status --short` to ensure no half-finished edits, dangling unstaged modifications, or accidentally staged files remain.

### 6.2 Full Regression & Quality Gate Pass
Run the full verification suite for the affected service(s) to verify that individual slices did not introduce cross-module regressions. Execute the actual commands configured for the service:

```bash
# Python service full quality gate
pytest
ruff check .
mypy .

# Frontend service full quality gate
npm run lint
npx tsc --noEmit
npm test
npm run build

# Multi-service / Compose validation (if applicable)
docker compose config
```

> [!IMPORTANT]
> **Verification Law Reminder:** You must run the actual verification commands and inspect the exit codes. Never state or imply that tests passed without executing them in your current session. Report exact counts: passed, failed, skipped, and execution duration.

### 6.3 Repository Workspace Hygiene Sweep
Inspect the repository for untracked files and artifacts:
```bash
git status -u
```
- Remove any temporary scratch files, debug dumps, or ad-hoc test scripts created in the working tree.
- Verify that no environment files (`.env`), private tokens, or binary build artifacts were left untracked in source directories.
- Confirm that `AGENTS.md` and `HANDOFF.md` are not staged or committed (per Repository Invariant 2).

### 6.4 Documentation & Tracking Updates
Synchronize project documentation with the code state:
1. **Implementation Plans:** In `Implementation_Plans/`, mark completed tasks and subtasks as `[x]`, recording any technical decisions or edge cases uncovered.
2. **Master Roadmap (`PLAN.md`):** Update milestone status or acceptance criteria checklist if the task completed a planned roadmap item.
3. **API Contracts (`contracts/`):** Ensure any schema, endpoint, or enum changes are reflected in OpenAPI specs and sample payloads.
4. **Handoff Document (`HANDOFF.md`):** If the repository uses `HANDOFF.md`, update it to document:
   - Current working state and completed objective.
   - Commit hashes created during this session.
   - Verified test results and regression status.
   - Known limitations, assumptions, and specific recommended next steps.

### 6.5 Final Task Completion Report
When reporting back to the user or caller agent, formulate a structured report containing:
1. **Summary of Changes:** What was implemented, broken down by 2–3 file slice.
2. **Commit Log:** List of commits created during the session with short hashes and commit messages (`git log -n <count> --oneline`).
3. **Verification Evidence:** Full commands executed, exit codes, and test/linter summaries (e.g., `42 passed in 1.83s`, `ruff: all checks passed`, `tsc: 0 errors`).
4. **Documentation Updates:** Links or paths to updated plans, contracts, or handoff notes.
5. **Known Limitations & Next Steps:** Unresolved edge cases, pending dependencies, or the next task to be executed.

---

# 3. Documentation hierarchy

| Order | Document | Authority and purpose |
|---:|---|---|
| 1 | `AGENTS.md` | Operational rules and coding-agent workflow |
| 2 | `HANDOFF.md`, if present | Current working state, active objective, blockers and next steps |
| 3 | `PROJECT.md` | Product scope, users, terminology and success criteria |
| 4 | `PLAN.md` | Master roadmap, milestones, dependencies and acceptance criteria |
| 5 | `CONTEXT_ARCHITECTURE.md` | Service boundaries, trust boundaries, data flows and failure behavior |
| 6 | `contracts/` | Cross-service API schemas, enums and sample payloads |
| 7 | `Implementation_Plans/` | Detailed, file-by-file plans for discrete features |
| 8 | Existing code, migrations and tests | Current implementation facts; inspect for divergence from docs |

When documents disagree:
1. Do not silently pick one and proceed.
2. Identify the exact conflict.
3. Prefer explicit, recent user-approved decisions over inferred assumptions.
4. Update the relevant source-of-truth document and contract once the decision is settled.
5. Keep implementation behavior and documentation aligned.

`PLAN.md` is the master plan. Do not duplicate all detailed implementation steps in it; put feature-level execution detail in `Implementation_Plans/`.

---

# 4. Architecture boundaries

CampusCue is organized as three independently deployable backend services plus the frontend.

## 4.1 Core API: source of truth

Owns:
- Authentication integration and server-side authorization.
- Clubs, memberships, events, resources, revisions, commitments, evidence references, tasks and dependencies.
- Event status transitions and provenance.
- Deterministic scheduling and transactional conflict enforcement.
- Scoped administrator overrides and audit history.
- Verified data assembly for reports.
- Service orchestration and frontend-facing APIs.

Must not:
- Delegate scheduling validity or authorization to an LLM.
- Treat an absent event record as proof of venue availability.
- accept client-supplied identity or `authorized_by` values as proof of authorization.

## 4.2 Agent API: bounded orchestration

Owns:
- Natural-language intent interpretation.
- Selecting from an explicit allowlist of typed tools.
- Calling Core API for operational facts and RAG API for source evidence.
- Explaining structured conflict and impact results.
- Drafting checklists, follow-ups, and reports.
- Returning structured action proposals, citations and tool traces.

Must not:
- Connect directly to the Core database.
- Execute arbitrary SQL, shell commands or unrestricted HTTP requests.
- Make up scheduling results, approvals, citations or tool outcomes.
- Perform unauthorized state changes or create administrator overrides.
- Send external messages or perform official status changes automatically in the MVP.

A proposed `book_event` natural-language action must resolve to the authorized workflow, normally proposal creation or request tracking. Official confirmation is a distinct operation requiring Core API authorization and evidence validation.

## 4.3 RAG API: document evidence

Owns:
- Approved source registry and document ingestion.
- Parsing, structure-aware chunking and metadata preservation.
- Document versioning, supersession and ingestion diagnostics.
- Sparse and dense retrieval, fusion and optional reranking.
- Evidence IDs, exact excerpts, page citations and grounded answers.
- Insufficient-evidence behavior and retrieval evaluation.

Must not:
- Determine current event status or live venue availability.
- Invent citations, source URLs, titles or page numbers.
- Pass content to generation before applying access filters.
- Treat retrieved document text as instructions that override system policy.
- Ingest private organizer exports or unapproved sensitive material.

## 4.4 Frontend

Owns interaction and presentation:
- Event proposal form and tentative calendar/list.
- Conflict display and explanation.
- Resource explorer and policy citations.
- Commitment timeline and change-impact review.
- Editable report drafts.

Must not be the enforcement point for authorization, status transitions, conflict rules, or admin overrides. All such checks must be repeated server-side.

## 4.5 Service communication

- Frontend calls the Core API for normal application operations.
- Core API calls Agent and RAG through typed HTTP contracts.
- Agent calls Core API tools for operational state and RAG for knowledge retrieval.
- Agent and RAG must be independently testable using mocks and must not require the whole system to start.
- Do not add queues, caches, extra databases, or services without a documented requirement and approved plan change.

---

# 5. Scheduling and event invariants

These rules are central to CampusCue. Read `PLAN.md` and `CONTEXT_ARCHITECTURE.md` before changing them.

## 5.1 Time representation

- Use timezone-aware timestamps only.
- Campus timezone is `Asia/Kolkata`.
- Interpret campus-local user input explicitly, then persist normalized instants in UTC.
- Reject ambiguous or invalid times rather than guessing.
- Use half-open intervals `[start_at, end_at)`.
- Require `start_at < end_at`.
- An event being edited must be excluded from comparisons against itself.

## 5.2 Two separate constraints

### Venue overlap
Confirmed events at the same venue must not overlap unless an explicitly authorized `VENUE_OVERLAP` override exists.

### Campus-wide minimum gap
The current product assumption requires at least 120 minutes between consecutive events across campus, even at different venues. Exactly 120 minutes passes; 119 minutes fails.

For events A and B, the gap is valid when:

```text
end_A + 120 minutes <= start_B
OR
end_B + 120 minutes <= start_A
```

This is a CampusCue planning assumption until verified by university stakeholders. Keep it configurable and do not describe it as official Amrita policy without evidence.

## 5.3 Conflict types

Keep conflict classes separate and typed:
- `VENUE_OVERLAP`
- `CAMPUS_GAP_VIOLATION`
- `TENTATIVE_OVERLAP`
- `DEPENDENCY_CONFLICT`
- `UNKNOWN_AVAILABILITY`

Do not compress every case into a generic boolean or a single ambiguous `conflict` string. Each result should identify relevant event IDs, time window, severity, explanation, and whether an override is required.

## 5.4 State and evidence

- Event lifecycle and individual commitment lifecycle are separate.
- `ACKNOWLEDGED` does not mean `CONFIRMED`.
- Official status changes require validated actor permissions and evidence/provenance.
- Organizer-reported claims must remain labeled as reported until verified.
- A change can mark prior commitments `NEEDS_REVALIDATION`; do not silently carry forward confirmations that may no longer apply.

## 5.5 Overrides

Overrides must be explicit and auditable. At minimum preserve scope, affected events, reason, authorized actor, timestamp and evidence reference where applicable.

- `CAMPUS_GAP` override affects only the campus-gap constraint.
- `VENUE_OVERLAP` override affects only the venue-overlap constraint.
- The Agent cannot authorize an override.
- Core API must authorize and validate it server-side.
- Never provide an unrestricted `ignore_conflicts=true` escape hatch.

## 5.6 Concurrency and transactions

A frontend or agent conflict check is advisory. Recheck constraints inside the transaction that performs the relevant write or confirmation. Protect against two concurrent requests both passing a stale pre-check.

Use appropriate PostgreSQL range queries, constraints and transaction/locking strategy. A same-venue exclusion constraint may help enforce confirmed venue non-overlap; the campus-wide gap constraint needs its own transaction-safe design. Add concurrency tests before claiming enforcement is reliable.

---

# 6. RAG engineering invariants

## 6.1 Ingestion and metadata
Preserve:
- Stable evidence/chunk ID.
- Document ID and title.
- Original source URL.
- Page start/end and section path when available.
- Document version and content hash.
- Access class.
- Ingestion timestamp and verification timestamp.
- Exact extracted chunk text.

Keep parsing failures visible. Do not claim page-level citations for formats or extraction paths that do not provide reliable page metadata.

## 6.2 Retrieval pipeline
The intended baseline is:

```text
Authorized documents
  → parse and preserve structure
  → structure-aware chunking
  → sparse retrieval (BM25/full-text)
  + dense retrieval (embeddings/pgvector)
  → Reciprocal Rank Fusion
  → optional reranking
  → access-filtered context selection
  → grounded answer and source citations
```

- Compare sparse-only, dense-only and hybrid retrieval on the same evaluation set.
- Tune chunk size, candidate count and reranking based on measurements.
- Keep `/retrieval/search` useful without an LLM.
- Apply document access filters before context reaches a model.
- Citations must be assembled from indexed metadata, not generated by the LLM.
- Support explicit insufficient-evidence responses.
- Do not treat embedding similarity as proof of truth or confidence.

## 6.3 RAG testing
Test:
- PDF/HTML parsing and page/section metadata.
- Exact keyword/acronym lookup.
- Paraphrased semantic queries.
- Hybrid fusion and reranking order.
- Citation integrity and exact excerpts.
- Access filtering.
- Superseded document behavior.
- Unanswerable questions and abstention.
- Provider/index failures and timeouts.

Use a reviewed evaluation set and track Recall@k, MRR or nDCG, citation correctness, answer faithfulness, abstention quality and latency where feasible.

---

# 7. Agent engineering invariants

## 7.1 Tools
Tools must be:
- Explicitly allowlisted.
- Typed and schema-validated.
- Small and domain-specific.
- Authorized by the service that owns the operation.
- Bounded by timeouts and a maximum call count.
- Observable through sanitized traces.

Initial tool candidates include:
- `check_event_conflicts`
- `create_event_draft`
- `get_event_details`
- `get_event_timeline`
- `request_event_change`
- `get_change_impact`
- `get_resource_details`
- `search_campus_policy`
- `get_event_checklist`
- `record_commitment`
- `create_followup_draft`
- `generate_event_report`

Only implement tools required by the active vertical slice. Tool names are not permission grants.

## 7.2 Execution controls
- Ask for missing critical fields rather than inventing dates, times, durations or venues.
- Use idempotency keys for retryable mutations.
- Use expected event revision/version to prevent stale writes.
- Bound tool calls, elapsed time, response size and retries.
- Validate model-generated tool arguments before execution.
- Treat user content, retrieved text and tool output as untrusted data.
- Do not report success until the called service returns a successful result.
- Distinguish proposed actions from executed actions.
- Consequential actions require human review in the MVP.
- Return citations/evidence IDs for policy claims.
- Retain a deterministic mock/demo provider path so tests do not require paid APIs.

## 7.3 Agent tests
Test tool selection, missing fields, malformed model output, timeouts, retries, idempotency, failed tools, stale event revisions, denied permissions, prompt injection and the absence of false success claims.

---

# 8. Data, security, and privacy rules

- Enforce authorization at every API boundary and for every object lookup/mutation.
- Do not trust a user ID, club ID, role, or `authorized_by` value merely because the client supplied it.
- Use least privilege for document ingestion and administrative actions.
- Keep internal Agent/RAG APIs private in integrated deployments; local host port publishing is for development only.
- Never commit real API keys, tokens, database passwords, private source documents or personal data.
- Keep `.env` local and provide safe `.env.example` placeholders.
- Avoid logging full sensitive prompts, private messages, document bodies, credentials, or participant data by default.
- Propagate request/correlation IDs across service boundaries.
- Keep audit logs for status changes, evidence verification and overrides.
- Separate synthetic demo data from real pilot data.
- Apply access controls before RAG retrieval, not only after answer generation.
- External LLM/embedding providers are data-egress boundaries; send only approved content.
- No automatic outbound email/message sending in the MVP.

---

# 9. Database and migration discipline

- Use incremental migrations.
- Never edit a migration that has already been applied in a shared or persistent environment. Add a new migration instead.
- Include appropriate foreign keys, `NOT NULL`, check constraints, indexes and uniqueness constraints.
- Keep domain validation in application code as well as database constraints where appropriate.
- Make multi-record mutations transactional.
- Preserve event revision and audit history; do not overwrite history to hide a previous state.
- Define deletion/cancellation semantics explicitly. Avoid cascading deletion of evidence/audit history unless the approved data-retention design requires it.
- Test migrations against a clean database and, when feasible, a database with representative existing records.
- If a migration fails, inspect the actual database state before attempting recovery. Never blindly reset or drop data.

---

# 10. Development, testing, and verification

## 10.1 Test layers

### Unit tests
Pure domain logic:
- Time interval overlap and two-hour gap boundaries (`[start_at, end_at)` calculations).
- Status transitions, entity lifecycle, and override scope validation.
- Input normalization, timezone normalization (`Asia/Kolkata` -> UTC), and schema validation.
- Agent tool argument validation, bounds checking, and tool-call parsers.
- RAG chunking, Reciprocal Rank Fusion (RRF), citation assembly, and metadata extraction.

### Integration tests
- Core API against PostgreSQL (foreign keys, transaction safety, locking).
- Transactional conflict enforcement and concurrency stress checks.
- Agent HTTP clients against mocked/stubbed Core and RAG servers.
- RAG retrieval against real test vector index/PostgreSQL test database.
- Authorization, role permissions, access filtering, and document versioning.

### HTTP/contract tests
Assert exact status codes, response envelopes, error codes, and schema compatibility. Avoid assertions that merely check that a response is non-null. Verify bidirectional compatibility against `contracts/*.openapi.yaml`.

### End-to-end tests
At minimum:
1. Create a tentative proposal.
2. Detect a tentative overlap against existing unconfirmed proposals.
3. Detect a same-venue overlap against confirmed events.
4. Detect a cross-venue gap violation (< 120 minutes).
5. Apply an authorized campus-gap override and verify it still rejects an unapproved venue overlap.
6. Change an event venue and mark relevant commitments for revalidation.
7. Answer a policy question with a valid source citation from indexed evidence.
8. Generate a report draft that flags missing facts without hallucinating.

---

## 10.2 Verification law

**No completion claims without fresh verification evidence.**

For every proposed modification:
1. Identify the exact command that proves the behavior.
2. Run the focused tests.
3. Run relevant formatting, linting, type-check, and build commands that actually exist in the workspace.
4. Inspect exit codes, stderr, and stdout.
5. Inspect `git diff` to confirm zero unintended changes.
6. Report exactly what passed, failed, or was not run.

Do not say “all tests pass” if only one test file was run. Do not hide pre-existing failures. Never claim a command ran or succeeded without actual execution output.

---

## 10.3 Root-cause debugging law

**No fixes without root-cause investigation first.**

1. Read the complete relevant trace, log, or error message.
2. Reproduce the smallest reproducible failure.
3. Inspect the boundary where the failure occurs: frontend schema, HTTP contract, service validation, database constraint, downstream dependency, or model/tool output.
4. Add or update an automated test that isolates and demonstrates the defect (RED).
5. Implement the smallest root-cause fix (GREEN).
6. Re-run the reproducer, relevant unit tests, and regression suite to confirm clean resolution.

---

## 10.4 The 2-3 file incremental commit protocol

When Git commits are authorized by the user, changes must be introduced in small, logically atomic increments of **at most 2 to 3 files per commit**. Monolithic commits touching multiple services or broad swathes of the tree are strictly forbidden.

### 10.4.1 Commit slicing anatomy
Every commit in a feature branch must represent a single coherent operational step:
- **Slice Type A (Contract / Schema):** 1 OpenAPI specification file + 1 sample payload fixture (e.g., `contracts/core-api.openapi.yaml` + `contracts/examples/event_proposal.json`).
- **Slice Type B (Domain Model / Migration):** 1 SQLAlchemy/data model + 1 Alembic migration script (or 1 domain model + 1 domain unit test).
- **Slice Type C (Core Business Logic):** 1 service logic file + 1 corresponding unit test (e.g., `services/core-api/src/services/conflicts.py` + `services/core-api/tests/unit/test_conflicts.py`).
- **Slice Type D (API Endpoint / Router):** 1 router/handler file + 1 HTTP integration test file (e.g., `services/core-api/src/api/routes/events.py` + `services/core-api/tests/integration/test_events_api.py`).
- **Slice Type E (Frontend Component):** 1 React component/hook + 1 component test or story (e.g., `apps/web/src/components/ConflictBanner.tsx` + `apps/web/src/components/ConflictBanner.test.tsx`).

### 10.4.2 Pre-commit staging verification
Before invoking `git commit`, verify that staging adheres to the slice boundary:
```bash
# Verify staged file count is strictly between 1 and 3 files
git status --short
git diff --cached --stat
```
If more than 3 files are staged, unstage the surplus files using `git restore --staged <file>` or `git reset HEAD <file>`. Never combine frontend and backend changes in the same commit. Never bundle schema migrations with UI components.

---

## 10.5 Service-specific pre-commit verification gates

Before any 2-3 file slice is committed, the service owning the modified files must pass its explicit verification gates. All commands must exit with status code `0`.

### 10.5.1 Python backend services (`services/core-api`, `services/agent-api`, `services/rag-api`)

When modifying Python service files, execute the following checks from the respective service directory:

1. **Targeted Unit Test Gate (Fast Feedback):**
   Execute only the test files directly exercising the modified modules:
   ```bash
   # Core API example
   pytest tests/unit/test_<modified_module>.py -v

   # Agent API example
   pytest tests/test_tools.py -k "test_<modified_tool>" -v

   # RAG API example
   pytest tests/test_retrieval.py -k "test_<modified_chunking>" -v
   ```
   *Requirement:* 100% pass rate on targeted tests. No skipped tests without documented justification.

2. **Linting and Formatting Gate (`ruff`):**
   Verify code style, import sorting, and syntax correctness on touched files:
   ```bash
   ruff check <path/to/modified_file_1.py> <path/to/modified_file_2.py>
   ruff format --check <path/to/modified_file_1.py> <path/to/modified_file_2.py>
   ```
   *Requirement:* Zero lint violations (`0 errors, 0 warnings`). If formatting issues exist, run `ruff format <files>` and re-verify.

3. **Static Type Safety Gate (`mypy`):**
   Verify type annotations, protocol compliance, and nullability:
   ```bash
   mypy <path/to/modified_file_1.py> <path/to/modified_file_2.py>
   ```
   *Requirement:* Clean type check (`Success: no issues found`). Never silence type errors using `# type: ignore` merely to pass the pre-commit gate.

### 10.5.2 Frontend React application (`apps/web`)

When modifying frontend components, hooks, utilities, or styles, execute the following checks from `apps/web`:

1. **Targeted Component Test Gate:**
   Execute the component or unit test covering the touched module:
   ```bash
   npm test -- src/components/<ModifiedComponent>.test.tsx --run
   # or vitest directly:
   npx vitest run src/components/<ModifiedComponent>.test.tsx
   ```
   *Requirement:* Component renders cleanly, assertion expectations pass, zero unhandled promise rejections.

2. **Static Linting Gate (`eslint`):**
   ```bash
   npm run lint -- src/components/<ModifiedComponent>.tsx
   # or root lint script if targeted execution is not configured:
   npm run lint
   ```
   *Requirement:* Zero errors. Do not suppress accessibility (a11y) or hook dependency warnings with `eslint-disable` comments.

3. **Global Type Safety Gate (`tsc`):**
   Frontend code imports shared types; type checks must verify whole-project type soundness:
   ```bash
   npx tsc --noEmit
   ```
   *Requirement:* Zero TypeScript diagnostics. All prop interfaces, API client response types, and imports must resolve completely.

### 10.5.3 Contracts and Shared Schemas (`contracts/`)

When modifying OpenAPI schemas, JSON schemas, or example fixtures under `contracts/`:

1. **Schema Validation Gate:**
   Validate OpenAPI syntax, valid JSON Schema definitions, and semantic correctness:
   ```bash
   # If spectral or openapi-cli is configured:
   npx @stoplight/spectral-cli lint contracts/*.openapi.yaml
   # Or using Python yaml/json validation tooling:
   python -c "import yaml; yaml.safe_load(open('contracts/core-api.openapi.yaml'))"
   ```
2. **Fixture Integrity Gate:**
   Verify that example JSON payloads conform strictly to the referenced OpenAPI schema components.
3. **Cross-Service Impact Check:**
   Verify that no required fields were added or enum variants removed without updating dependent client mocks in `services/agent-api` and `apps/web`.

---

## 10.6 The "No Commit Without Fresh Evidence" invariant

Every commit in CampusCue must be backed by concrete, fresh test and lint execution evidence captured in the current session.

### 10.6.1 Execution checklist prior to `git commit`
Before executing any commit:
1. **Status Inspection:** Run `git status --short` and confirm exact files to be committed.
2. **Diff Review:** Run `git diff --cached` to verify no stray `print()`, `console.log()`, temporary debug flags, or unauthorized file edits are included.
3. **Gate Execution:** Run the service-specific gates (Tests -> Linter -> Type checker) in sequence.
4. **Exit Code Verification:** Confirm all exit codes are `0`.
5. **Commit Construction:** Write a descriptive, scoped commit message following Conventional Commits (e.g., `feat(core-api): add same-venue interval overlap detection`).

### 10.6.2 Handling failing tests and broken gates
- **Never bypass verification:** The `--no-verify` (`-n`) Git flag is strictly prohibited under all circumstances.
- **Never commit broken builds:** Staging broken code to "save progress" is forbidden. Uncommitted progress remains in the working tree or a local stash.
- **Root-cause first:** If a unit test or type check fails, do not loosen assertions or disable checks. Follow Section 10.3 to fix the underlying issue.
- **Distinguish pre-existing failures:** If a test outside the current 2-3 file slice is already failing on the branch, document the specific pre-existing failure in the handoff or task report. Do not allow your change to introduce new failures or mask existing ones.

---

## 10.7 Handling partial feature states across 2-3 file batches

Complex features in CampusCue (such as Change-Impact Analysis or Deterministic Scheduling) span more than 2-3 files in total. To maintain continuous branch health while adhering to small commit increments, partial feature states must be engineered with care.

### 10.7.1 The "Always Green, Always Compilable" standard
Every intermediate commit in a multi-commit sequence must leave the repository in a fully compilable, test-passing state:
- **No broken imports:** Never import a function, class, or type that has not yet been committed or defined. If Slice 2 relies on a helper from Slice 1, Slice 1 must be committed first.
- **No syntax errors:** An unfinished function must contain a valid stub (e.g., `raise NotImplementedError(...)` or a typed placeholder return) rather than incomplete syntax.
- **No orphaned contract types:** If a TypeScript type or Pydantic model is added, it must be syntactically valid and pass type checking even if no router uses it yet.

### 10.7.2 Phased slice progression
Organize multi-commit features in a bottom-up, dependency-driven sequence:

```text
Commit 1 (Contracts & Core Types):
  - contracts/core-api.openapi.yaml
  - contracts/examples/conflict_check.json
  -> Pass: Schema linting

Commit 2 (Domain Calculus & Unit Tests):
  - services/core-api/src/domain/intervals.py
  - services/core-api/tests/unit/test_intervals.py
  -> Pass: pytest, ruff, mypy

Commit 3 (Database Query / Repository Layer):
  - services/core-api/src/db/repositories/events.py
  - services/core-api/tests/integration/test_event_repo.py
  -> Pass: pytest, ruff, mypy

Commit 4 (API Router & Integration Test):
  - services/core-api/src/api/routes/conflicts.py
  - services/core-api/tests/integration/test_conflicts_route.py
  -> Pass: pytest, ruff, mypy

Commit 5 (Frontend API Client & UI Component):
  - apps/web/src/api/conflicts.ts
  - apps/web/src/components/ConflictWarning.tsx
  - apps/web/src/components/ConflictWarning.test.tsx
  -> Pass: vitest, eslint, tsc
```

### 10.7.3 Feature flagging and dormant code paths
When an API route or service method is only partially complete and requires subsequent commits to be fully functional:
- Keep the endpoint dormant or unrouted until the handler is fully implemented.
- If an endpoint is exposed, it must return an explicit `501 Not Implemented` with a standard error envelope, rather than crashing with unhandled exceptions.
- Frontend components should not be mounted on user-facing pages until their supporting hooks and mock/real endpoints pass integration tests.

---

# 11. Parallel work and integration discipline

CampusCue has four practical workstreams:

| Workstream | Owns |
|---|---|
| Core API | Data model, migrations, event/resource APIs, scheduling, authorization, revisions, evidence and overrides |
| Agent API | LLM abstraction, typed tools, orchestration, explanations, action drafts and agent tests |
| RAG API | Ingestion, metadata, sparse/dense retrieval, fusion, reranking, citations and retrieval evaluation |
| Frontend | Event proposal/calendar, resources, policy assistant, conflict display, impact review and report editor |

## 11.1 Parallel development rules
- Freeze shared schemas early in `contracts/`.
- Each team must have a mock-based development/test path.
- Frontend starts with fixtures rather than waiting for live services.
- Agent uses mocked Core/RAG clients until contracts are stable.
- RAG search/evaluation works independently of the Agent.
- Do not silently rename shared fields, change enum meanings, or change timestamp semantics.
- A contract change must update OpenAPI schemas, example payloads, contract tests, and dependent workstream notes in the same change.
- Integrate a vertical slice early; do not leave all integration until the end.
- Coordinate changes to shared contract files rather than editing them concurrently without agreement.

## 11.2 Coordinating incremental (2–3 file) commits across service boundaries

Cross-service features must be broken down into disciplined, self-contained micro-commits spanning at most 2–3 tightly coupled files. This prevents massive integration bottlenecks, circular dependencies, and broken intermediate branch states.

### 11.2.1 Contract-first commit protocol
Cross-boundary work proceeds through three sequenced commit phases:

```text
Phase 1: Contract Commit  ──▶  Phase 2: Mock & Consumer Commit  ──▶  Phase 3: Service Implementation
(`contracts/` schema + fixture)  (Mock client + consumer test)       (Endpoint handler + domain logic)
```

1. **Phase 1: Authoritative Contract Commit (`contracts/`)**
   - **Scope (1–2 files):** The OpenAPI YAML/JSON schema definition and accompanying canonical JSON fixtures under `contracts/`.
   - **Protocol:** Any new endpoint, schema modification, or field addition MUST be committed to `contracts/` before consumers or backend implementers commit dependent code. Neither service implementers nor consumer callers may commit code targeting an uncommitted or draft contract.
   - **Integrity Rule:** Schema changes must pass contract linting/validation prior to commit. Once committed, the contract revision serves as an immutable boundary specification for parallel development.

2. **Phase 2: Mock Clients and Contract Fixtures Commit**
   - **Scope (2–3 files):** Consumer mock adapter/fixture handler + consumer unit/integration test.
   - **Protocol:** Consumers (Frontend calling Core API, or Agent API calling Core/RAG APIs) do not wait for live backend endpoints. They commit a typed mock client or HTTP mock handler (e.g., MSW handlers for Frontend, `pytest-mock` / `respx` responses for Agent) mirroring the exact schema from Phase 1.
   - **Green State Guarantee:** The consumer's test suite verifies functionality against the mock. Intermediate commits remain green in CI without requiring the real backend service to run or exist yet.

3. **Phase 3: Service Implementation Commit**
   - **Scope (2–3 files):** Controller/router handler + domain service/database operation + service integration test.
   - **Protocol:** The implementing service (Core API or RAG API) implements the concrete logic and validates output against contract-driven tests. Once merged, integration suites can flip environment flags from mock adapters to live service instances.

### 11.2.2 Mocking discipline and intermediate green states
- **Zero Broken Intermediate Commits:** Every intermediate commit pushed to a branch or integrated into `main` must pass baseline linters, type checks, and service-level test suites. Committing incomplete code that breaks downstream compilation or CI builds is prohibited.
- **Atomic Consumer + Mock Changes:** Whenever consumer code introduces a call to a new or updated endpoint, the mock fixture and client mock handler must be included in that exact commit. Never commit consumer changes that invoke an unmocked, non-existent backend endpoint.
- **Contract Fidelity in Mocks:** Mock responses must strictly reflect canonical behavior, including:
  - Preserving the standard error envelope (`code`, `message`, `details`, `request_id`).
  - Strict timestamp formatting (ISO 8601 UTC representation with campus `Asia/Kolkata` input handling).
  - Explicit conflict payload structures with typed conflict classes.

## 11.3 Branch and merge discipline for incremental commits

### 11.3.1 Short-lived feature branches and micro-commits
- **Branch Lifetime:** Keep feature branches short-lived (hours to at most 1–2 days). Long-running feature branches accumulating sprawling multi-service diffs are prohibited.
- **Micro-Commit Scope:** Restrict each commit to 2–3 logically linked files (e.g., `schema.yaml` + `sample.json`; `client.ts` + `client.test.ts`; `migration.sql` + `repository.py`).
- **Commit Early and Often:** Commit small, verifiable vertical steps rather than waiting for an entire multi-service feature to be fully completed.

### 11.3.2 Avoiding large merge conflicts through frequent rebase
- **Continuous Trunk Rebase:** Before starting work on any 2–3 file slice and prior to merging, rebase the local feature branch onto the latest `main`:
  ```bash
  git fetch origin
  git rebase origin/main
  ```
- **Strict Directory Boundaries:** Workstreams must isolate their code changes to their designated service roots (`core/`, `agent/`, `rag/`, `frontend/`). Shared touches outside these boundaries are restricted to `contracts/` and root configuration.
- **Contract Coordination Lock:** If multiple workstreams require changes in `contracts/`, they must coordinate ordering. One workstream commits the contract schema first; peer workstreams immediately rebase onto that commit before making further consumer changes.

### 11.3.3 Atomic multi-service changes and contract evolution
When evolving schemas that affect multiple services, adhere to backwards-compatible deprecation or atomic integration:

1. **Additive Evolution (Preferred):**
   - New endpoints, optional fields, or non-breaking extensions should be introduced additively.
   - Sequence: Commit contract addition -> Update consumer mocks -> Implement backend handler -> Switch consumer to new fields.

2. **Breaking Changes (Two-Phase Rollout):**
   - For required field modifications, renames, or enum adjustments, avoid abrupt single-step breaking changes.
   - **Expand Phase:** Add the new field or endpoint in `contracts/` while retaining the deprecated property. Update backend logic to accept both shapes.
   - **Migrate Phase:** Update consumers across discrete 2–3 file commits to adopt the new schema shape.
   - **Contract Phase:** Once all consumers have migrated, remove the deprecated field in `contracts/` and decommission legacy backend handling.

3. **Atomic Multi-Service Integration:**
   - In cases where a breaking contract change cannot be phased and must land across services simultaneously in a unified repository, it must be structured as an atomic multi-service changeset that updates:
     1. The authoritative schema in `contracts/`.
     2. Mock fixtures and test assertions in consumer services (`frontend/`, `agent/`).
     3. Request handlers, domain models, and integration tests in producer services (`core/`, `rag/`).
   - All affected service suites (`pytest`, `npm test`, contract schema validators) must pass simultaneously before merging.

## 11.4 Required shared conventions
- Stable UUIDs for persistent entities.
- ISO 8601 timezone-aware timestamps.
- `Asia/Kolkata` for campus-facing date/time interpretation and display.
- Stable error envelope: `code`, `message`, `details`, `request_id`.
- Conflict objects distinguish type, severity, affected events, interval, explanation and override requirements.
- RAG citations use stable evidence IDs and indexed source metadata.
- Mutations that can be retried support idempotency.
- Event changes carry expected revision/version.

---

# 12. Repository layout guidance

Inspect the actual repository before creating or moving directories. The following is a target shape, not permission to overwrite an existing structure:

```text
campuscue/
├── AGENTS.md
├── HANDOFF.md                    # if the repository adopts this protocol
├── PROJECT.md
├── PLAN.md
├── CONTEXT_ARCHITECTURE.md
├── README.md
├── IMPLEMENTATION_INDEX.md
├── Implementation_Plans/
├── contracts/
│   ├── CONTRACTS.md
│   ├── core-api.openapi.yaml
│   ├── agent-api.openapi.yaml
│   ├── rag-api.openapi.yaml
│   └── examples/
├── prompts/
├── apps/
│   └── web/
├── services/
│   ├── core-api/
│   ├── agent-api/
│   └── rag-api/
├── docker-compose.yml
└── .env.example
```

The actual framework, folder names and package managers must follow the decisions and code already present in the repository. Do not create duplicate architecture documents or alternative agent instruction files without an explicit reason.

---

# 13. Docker and local service rules

Suggested development ports:
- Web: `3000`
- Core API: `8000`
- Agent API: `8001`
- RAG API: `8002`
- PostgreSQL: `5432`

Treat these as defaults only; inspect existing configuration before changing ports.

- Each backend service must have its own dependency manifest, Dockerfile, tests and documented startup command.
- Each service should run independently using mocks or a minimal test configuration where practical.
- Compose must use health/readiness checks for required dependencies.
- `/health` should indicate process liveness.
- `/ready` should indicate whether dependencies required for that service's advertised behavior are ready.
- Do not make optional LLM providers a requirement for deterministic Core API health.
- In an integrated environment, keep Agent and RAG on a private network unless direct access is explicitly required and protected.
- Do not publish database or internal service ports publicly by default.
- Keep credentials in environment variables or a proper secret mechanism, never in source code.

---

# 14. Task planning and implementation plans

Every non-trivial feature requires an implementation plan under `Implementation_Plans/` before broad implementation begins. Plans bridge architectural constraints with operational execution, ensuring changes remain incremental, verifiable, and safe.

A plan must include:
1. **Objective and non-goals:** Precise description of the capability being added and explicit boundaries of what will not be touched.
2. **Preconditions, dependencies and assumptions:** Required services, external libraries, database state, or contracts that must be in place.
3. **Owning service and affected contracts:** Which service owns the business logic and any OpenAPI schemas impacted.
4. **Ordered 2–3 file execution batches:** Decomposed vertical slices with explicit file limits.
5. **Expected commit checkpoints:** Pre-specified commit types, scopes, messages, and file lists for each batch.
6. **Data model and migration changes:** Exact database DDL, constraints, indexes, and rollback strategy.
7. **Testing matrix:** Unit, integration, concurrency, boundary, failure, and authorization test cases.
8. **Definition of done:** Batch-level and overall feature completion criteria.
9. **Risks, concurrency, and rollback considerations:** Failure modes, cross-service impacts, and mitigation.
10. **Deviation log:** Live audit of modifications to the plan during execution.

---

## 14.1 Bounded vertical slicing (the 2–3 file batch rule)

Broad, cross-cutting edits spanning many files obscure regressions, break rollback safety, and make code review difficult. To maintain strict blast-radius control, every implementation plan must decompose feature delivery into ordered, discrete execution batches strictly limited to **2–3 files per batch**.

Each batch must represent a coherent, self-contained architectural stratum that compiles, passes linting, and can be verified independently:

### Standard backend slicing archetype
- **Batch 1: Persistence stratum (schema + migration)**
  - Scope: Database migration file and ORM/table schema definition (2 files).
  - Example: `services/core-api/migrations/0004_event_overrides.sql` + `services/core-api/app/models/override.py`.
- **Batch 2: Domain & data access stratum (repository + service logic)**
  - Scope: Data access repository and core business logic or domain validator (2 files).
  - Example: `services/core-api/app/repositories/override_repo.py` + `services/core-api/app/domain/scheduling.py`.
- **Batch 3: Transport & validation stratum (schemas + route handler)**
  - Scope: Request/response schemas and API route endpoint (2 files).
  - Example: `services/core-api/app/schemas/override.py` + `services/core-api/app/api/routes/overrides.py`.
- **Batch 4: Verification stratum (tests + contract fixture)**
  - Scope: Targeted integration/unit test suite and shared contract fixture or OpenAPI spec update (2–3 files).
  - Example: `services/core-api/tests/integration/test_overrides.py` + `contracts/examples/override_response.json`.

### Standard frontend slicing archetype
- **Batch 1: Types & client stratum:** API client service/SDK method + TypeScript interface definitions (2 files).
- **Batch 2: Presentation stratum:** UI component + component stylesheet or preview fixture (2 files).
- **Batch 3: Integration stratum:** Page/container wiring + end-to-end or interaction test (2 files).

### Batch definition of done (DoD)
A batch is complete only when:
1. All files listed in the batch have been written or updated.
2. The code compiles without type errors, lint warnings, or broken imports.
3. The focused verification test for that batch passes.
4. The repository is left in a valid, functional intermediate state—no broken references or partially implemented syntax errors.

---

## 14.2 Expected commit point specification

Plans must treat commit checkpoints as first-class architectural specifications. While **Git Invariant 1** mandates that an agent must never execute `git commit` unless explicitly authorized by the user, every plan must pre-define the exact commit structure so that when commit authority is granted (or when a developer commits), work is committed in clean, atomic increments.

For every batch, the plan must explicitly document:
1. **Target files:** The exact relative paths to be created, modified, or deleted (maximum 3 files).
2. **Commit type and scope:** Standard Conventional Commit prefix (e.g., `feat(core-api):`, `test(rag-api):`, `fix(agent-api):`).
3. **Commit message:** A concise imperative summary (under 72 chars) with bullet points detailing the structural changes.
4. **Verification command:** The exact test or lint command that must succeed prior to checkpoint sign-off.

### Commit checkpoint specification format
In the plan, each batch must be specified using this standard structure:

```markdown
### Batch 2: Override Repository and Service Enforcement
- **Files:**
  - `services/core-api/app/repositories/override_repo.py`
  - `services/core-api/app/domain/scheduling.py`
- **Verification:** `pytest services/core-api/tests/unit/test_scheduling.py`
- **Expected Commit:**
  - **Type:** `feat(core-api)`
  - **Message:** `feat(core-api): add override repository and transactional scheduling checks`
  - **Details:**
    - Add scoped override queries by event ID and conflict type.
    - Implement transactional conflict check excluding approved overrides.
- **Batch Definition of Done:** Unit tests pass; repository methods handle empty/not-found states gracefully.
```

---

## 14.3 Managing deviations and scope creep

During implementation, unforeseen dependencies, missing abstractions, or edge cases will inevitably arise. An agent or developer must never silently expand a 2–3 file batch into a wide, sprawling diff.

### Deviation triggers
A plan deviation occurs whenever:
- A batch requires editing or creating more than 3 files to complete its objective.
- An unexpected architectural prerequisite is uncovered (e.g., missing database column, unmodeled foreign key, missing auth helper).
- An existing API contract or shared enum must change to support the batch.
- A planned approach proves technically infeasible or introduces a regression.

### The Stop-and-Split protocol
When a deviation trigger occurs:
1. **Hard Stop:** Halt code modification immediately. Do not touch additional files beyond the current 2–3 file boundary.
2. **Root-Cause Analysis:** Diagnose why the extra files or changes are needed.
3. **Sub-Batch Slicing:** Break the work into smaller sub-batches (e.g., split Batch 2 into `Batch 2a: Prerequisite Foundation` and `Batch 2b: Service Enforcement`), ensuring each remains strictly within the 2–3 file limit.
4. **Update the Plan's Deviation Log:** Before proceeding to write code or stage a commit checkpoint, log the deviation in the implementation plan's `## Deviation log` section with:
   - **Date and batch number.**
   - **Reason for deviation:** The technical driver or missing prerequisite.
   - **Adjustment made:** The new sub-batches or modified file list.
   - **Safety assessment:** Confirmation that no breaking changes or unauthorized behavior were introduced.
5. **Resume Execution:** Proceed with the newly documented sub-batch using the standard verification and checkpoint workflow.

---

## 14.4 Implementation plan markdown template

All new implementation plans under `Implementation_Plans/` must adhere to this standard template:

```markdown
# Implementation Plan [NN]: [Feature Name]

**Status:** Planned | In Progress | Complete  
**Owner:** [Core API | Agent API | RAG API | Frontend]  
**Dependencies:** [Plan references, database migrations, or contracts]

## 1. Objective and Non-goals
- **Objective:** [Clear description of functional capability]
- **Non-goals:** [Explicitly excluded capabilities or future enhancements]

## 2. Affected Contracts and Boundaries
- `contracts/...`
- API endpoints: `METHOD /path`

## 3. Ordered Execution Batches (2–3 Files Per Batch)

### Batch 1: [Stratum Name, e.g., Persistence Model & Migration]
- **Files:**
  - `path/to/file1`
  - `path/to/file2`
- **Verification:** `[pytest / npm test command]`
- **Expected Commit:**
  - **Type:** `feat([service])` | `fix(...)` | `refactor(...)`
  - **Message:** `[prefix]: [imperative description]`
- **Definition of Done:** [Criteria for completion]

### Batch 2: [Stratum Name, e.g., Repository & Domain Logic]
- **Files:**
  - `path/to/file1`
  - `path/to/file2`
- **Verification:** `[command]`
- **Expected Commit:**
  - **Type:** `feat([service])`
  - **Message:** `[prefix]: [imperative description]`
- **Definition of Done:** [Criteria for completion]

### Batch 3: [Stratum Name, e.g., API Route & Schemas]
- **Files:**
  - `path/to/file1`
  - `path/to/file2`
- **Verification:** `[command]`
- **Expected Commit:**
  - **Type:** `feat([service])`
  - **Message:** `[prefix]: [imperative description]`
- **Definition of Done:** [Criteria for completion]

## 4. Verification and Test Matrix
- Unit tests: [test paths and cases]
- Integration/Contract tests: [test paths and cases]
- Concurrency/Boundary tests: [specific scenarios]

## 5. Overall Definition of Done
- [ ] All batch verification commands pass.
- [ ] No batch touched more than 3 files without a recorded deviation.
- [ ] Contracts and OpenAPI specifications match implementation.
- [ ] Invariants verified (Asia/Kolkata timestamps, transactional checks, etc.).

## 6. Deviation Log
- [Date] - Initial plan created.
- [Date] - Batch [N] deviation: [Reason, file adjustment, and sub-batch resolution].
```

---

## 14.5 Recommended milestone implementation order

To ensure parallel workstreams integrate smoothly without circular dependencies:

1. Foundation and contracts.
2. Core event model and deterministic scheduling.
3. RAG ingestion and hybrid retrieval baseline.
4. Agent tools against mocks, then real service contracts.
5. Frontend vertical slice using mocks, then integration.
6. Change-impact flow.
7. Report draft.
8. End-to-end hardening and demo preparation.

Do not block independent teams on full completion of another service. Establish mock interfaces first.

---

# 15. Handoff maintenance

If `HANDOFF.md` exists or the repository has adopted a handoff log, update it before ending a coding task. Preserve its established format rather than replacing it with a new template.

At minimum record:
1. Session/task summary.
2. Current project state.
3. Active objective.
4. Changes made.
5. Architectural decisions and assumptions.
6. Dependencies added/removed.
7. Environment/configuration changes.
8. Database/migration changes.
9. API contract changes.
10. Bugs fixed.
11. Known issues and blockers.
12. TODO/next steps.
13. Testing status with actual commands and outcomes.
14. Performance/latency notes if measured.
15. Important context for the next agent.
16. Files touched.
17. Suggested starting point for the next agent.

If no `HANDOFF.md` exists, do not invent prior state. Create one only if requested by project workflow or clearly useful and consistent with the repository's conventions.

---

# 16. Completion report

Every coding task must conclude with an evidence-backed, factual completion report. Changes must be delivered in atomic, incremental batches of 2–3 files per commit. The completion report must document every individual commit batch alongside its isolated verification proof.

Do not include generic or unsubstantiated claims such as “production-ready” or “all tests pass.” Never claim tests, commits, deployments, or integrations that were not actually run and inspected.

### 16.1 Required report format

1. **Executive summary:** Concise summary of behavior implemented, refactored, or investigated.
2. **Incremental commit record (2–3 file batch protocol):**
   Document the exact sequence of incremental commits. Every commit must contain no more than 2–3 related files, accompanied by verification proof demonstrating tests passed prior to creating that commit:

   | Commit SHA | Commit Message | Files Included (Max 2–3) | Pre-Commit Verification & Outcome |
   |:---|:---|:---|:---|
   | `<short-sha>` | `<type>(<scope>): <subject>` | `path/to/file1.py`, `path/to/file2.py` | `pytest tests/unit/test_foo.py` (12 passed, exit code 0) |
   | `<short-sha>` | `<type>(<scope>): <subject>` | `path/to/file3.py`, `contracts/foo.yaml`, `tests/test_foo.py` | `pytest tests/test_foo.py` && `ruff check .` (exit code 0) |

3. **Batch verification proof:**
   - Detailed terminal command, exit code, and test execution outcome for **each** individual commit batch before that commit was created.
   - Comprehensive regression check across the affected service (e.g., full service test suite, linter, type check).
4. **Working tree and repository hygiene:**
   - Verifiable output of `git status --short`.
   - Proof that no untracked scratch files, temporary test logs, or debug artifacts remain in the workspace.
   - Explicit confirmation that `AGENTS.md` and `HANDOFF.md` remain unstaged and uncommitted (unless explicit user authorization was granted).
5. **Contracts, schemas, and migrations:**
   - Exact specifications of modified OpenAPI contracts, schemas, or database migrations.
   - Backwards-compatibility and downstream dependency impact assessment.
6. **Known limitations and unverified areas:**
   - Specific edge cases, missing mocks, network-dependent integrations, or performance characteristics not exercised.
7. **Implementation plan deviations:**
   - Transparent explanation of any departures from the approved implementation plan or contract specifications.
8. **Next immediate step:**
   - The single most logical, actionable follow-up task for the next developer or agent.

---

# 17. Hard invariants checklist

Before declaring any CampusCue task or vertical slice complete, verify every applicable item. Every box must be checked against real, fresh evidence:

### Process, Git, and hygiene invariants
- [ ] **Context alignment:** Read `AGENTS.md`, `HANDOFF.md` (if present), `PROJECT.md`, `PLAN.md`, and relevant implementation plans before editing.
- [ ] **User changes preserved:** Inspected `git status` and existing diffs; did not overwrite or discard user changes.
- [ ] **Incremental commit protocol (2–3 files):** All changes were committed in small, cohesive batches of 2–3 files. No monolithic commits.
- [ ] **Pre-commit test verification:** Verified that focused unit/integration tests and linters passed cleanly prior to creating *every individual commit batch*.
- [ ] **Operational doc preservation:** Verified that `AGENTS.md` and `HANDOFF.md` are preserved and NOT improperly committed or staged without authorization.
- [ ] **Clean working tree inspection:** Verified `git status --short`; confirmed no leftover scratch scripts, temporary files, build artifacts, or unintended modifications remain.
- [ ] **Final diff review:** Inspected `git diff` to ensure zero unintentional whitespace changes, dead code, or stray edits.

### Architectural and domain invariants
- [ ] **Core API authority:** Kept operational state, authorization, event lifecycle, and scheduling truth strictly inside Core API (never delegated to LLM).
- [ ] **Bounded Agent orchestration:** Agent tools remain strictly allowlisted, typed, parameter-validated, timeout-bounded, and permission-checked.
- [ ] **Grounded RAG citations:** Citations are assembled strictly from indexed source metadata and chunk IDs; no synthetic citations or hallucinated policies.
- [ ] **Lifecycle distinctions:** Preserved explicit domain separation between `TENTATIVE`, `REQUESTED`, `ACKNOWLEDGED`, and `CONFIRMED`.
- [ ] **Independent conflict classes:** Maintained strict typing and independent handling for `VENUE_OVERLAP` vs. `CAMPUS_GAP_VIOLATION`.
- [ ] **Availability truth:** Never inferred venue availability from an empty calendar or absent event record.
- [ ] **Transactional enforcement:** Re-checked conflict constraints within the database write transaction to protect against concurrent stale passes.

### Quality and documentation invariants
- [ ] **Meaningful tests added/updated:** Covered success paths, edge boundaries, conflict detections, and authorization failures.
- [ ] **Fresh verification executed:** Ran real verification commands (unit tests, contract validation, type checks) and inspected actual exit codes and outputs.
- [ ] **Contracts and plans updated:** Synchronized OpenAPI specs, mock payloads, and implementation plans with any code-level contract changes.
- [ ] **Handoff maintenance:** Updated `HANDOFF.md` according to repository protocol if applicable.
- [ ] **Accurate reporting:** Completion report lists commit batches, per-batch verification proof, known limitations, and next steps without unsubstantiated claims.
