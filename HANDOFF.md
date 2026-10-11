# HANDOFF: CampusCue backend and AI workstream

> **Updated:** 2026-10-11 (third session). Sections 1 and 'State as of 2026-10-11' are current; sections 3, 5, 7, 8, 15 and 17 were written on 2026-10-10 and are partly superseded (marked below).
> **Branch:** `backend-ai`, code HEAD `9655858`, merged with `origin/main` (`0c8273e`), **21 local commits not pushed**. **Owner of this workstream:** Shruhath (git author `Shruhath`); the teammate Mrudula also pushes to this branch.
> **If you read nothing else, read sections 1, 2, 3 and 21.**

This file follows the 17-item handoff list in `AGENTS.md` section 15 and adds the context a cold-start agent needs: working rules, a map of the code, the exact design of the next milestone, and the traps the previous session fell into. Everything here was checked against the repository on the day it was written. Where something is a recommendation and not a fact, it says so.

---

## Table of contents

1. [One-minute summary](#1-one-minute-summary)
2. [Working rules (non-negotiable)](#2-working-rules-non-negotiable)
3. [Where you are and what to do first](#3-where-you-are-and-what-to-do-first)
4. [People, ownership and coordination](#4-people-ownership-and-coordination)
5. [Repository and git state](#5-repository-and-git-state)
6. [Architecture in brief](#6-architecture-in-brief)
7. [What exists, layer by layer (Core API)](#7-what-exists-layer-by-layer-core-api)
8. [What exists (Agent API)](#8-what-exists-agent-api)
9. [The write path, step by step](#9-the-write-path-step-by-step)
10. [Database and migrations](#10-database-and-migrations)
11. [API contracts](#11-api-contracts)
12. [Tests, gates and how to run everything](#12-tests-gates-and-how-to-run-everything)
13. [Dependencies, environment and configuration](#13-dependencies-environment-and-configuration)
14. [Bugs found and fixed this session](#14-bugs-found-and-fixed-this-session)
15. [Known issues, gaps and blockers](#15-known-issues-gaps-and-blockers)
16. [Decisions still open](#16-decisions-still-open)
17. [The next milestone, designed in detail (P12 to P15)](#17-the-next-milestone-designed-in-detail-p12-to-p15)
18. [After the HTTP milestone](#18-after-the-http-milestone)
19. [Traps and lessons learned](#19-traps-and-lessons-learned)
20. [Performance and measurements](#20-performance-and-measurements)
21. [Suggested starting point](#21-suggested-starting-point)
22. [Appendix A: commit ledger](#appendix-a-commit-ledger)
23. [Appendix B: file map with sizes](#appendix-b-file-map-with-sizes)
24. [Appendix C: helper scripts to recreate](#appendix-c-helper-scripts-to-recreate)

---

## 1. One-minute summary

CampusCue is an AI-assisted event-operations workspace for student clubs at Amrita Vishwa Vidyapeetham, Coimbatore. It is being built for a hackathon. Four services: **Core API** (source of truth, :8000), **Agent API** (bounded LLM orchestration, :8001), **RAG API** (policy documents, :8002), **Web** (:3000), plus **PostgreSQL 18**.

This workstream owns **Core API and Agent API**. The RAG API and the web UI belong to a teammate (Mrudula). Do not edit their areas without being asked.

**State as of 2026-10-11 (current; supersedes the earlier summary table):**

| Area | State |
|---|---|
| Architecture | `docs/architecture/architecture-campuscue-backend-ai-2026-10-10/ARCHITECTURE-SPINE.md`, status `final`, 23 decisions (AD-1 to AD-23) |
| Core domain, persistence, write path | Done and race-proved on PostgreSQL 18 (see sections 7, 9, 10) |
| Core HTTP, real routes | `POST /api/v1/auth/demo-login`; `POST/GET /api/v1/events`; `GET /api/v1/events/{id}`; `POST /api/v1/events/{id}/conflict-check`; `POST /api/v1/events/{id}/transitions`; `POST /api/v1/overrides`; `GET /api/v1/resources[/{id}]`; **`POST /internal/v1/agent-tools/check_event_conflicts` and `GET /internal/v1/agent-tools/events/{id}`**; `/health`, `/ready` |
| Core HTTP, still 501 stubs | `POST /api/v1/agent/chat`; `GET /api/v1/agent-actions`; `POST /api/v1/agent-actions/{id}/confirm` and `/reject`; `POST /internal/v1/agent-actions` (it already requires both facade credentials, then answers 501) |
| Agent facade security | Done: delegation tokens (`app/clients/delegation.py`: HS256, `aud=agent-tools`, at most 120 s, lifetime re-checked on verify), `DelegationService` (organizer-class only; loads the user from the database on every call and flags them `via_agent`), `require_internal_key` (constant-time, fails closed if unconfigured) and `require_delegated_actor` in `app/api/deps.py`, wired in `container.py` and `main.py`. Proven on real PostgreSQL in `tests/integration/test_facade_sql.py` (a revoked membership takes effect while the token is still valid; a deleted user is 401; a delegation is refused on public routes and a session on the facade) |
| Agent API | Real HTTP clients (Core, RAG), LLM port (`app/ports/llm.py`) with Groq and fake providers, bounded orchestration engine, tool allowlist, real `/v1/agent/chat`, `/plan-event`, `/analyze-change`. Its Core client now calls the published facade paths. **Reads work against Core; filing a proposal cannot until Core persists agent actions.** |
| RAG and Web | The teammate's: real retrieval and answer routes, and a dashboard UI, merged to `main` |
| Seeds | `scripts.seed_demo` is idempotent and compose runs it after migrations. Personas: `campus-admin@demo.invalid`, `club-admin@demo.invalid`, `organizer@demo.invalid`, `outsider@demo.invalid` |

**Verified local compose smoke (2026-10-11):** with `POSTGRES_PASSWORD=campuscue`, run `docker compose up --build -d postgres minio migrate seed-demo core-api agent-api`; then `curl http://localhost:8000/ready`, `curl http://localhost:8001/ready`, and `curl -X POST http://localhost:8000/api/v1/auth/demo-login -H 'content-type: application/json' --data '{"email":"organizer@demo.invalid"}'`. PostgreSQL, MinIO, migrations, seed data, both readiness probes and demo login succeeded. The MinIO image is a pinned mirror because the historical official Docker Hub image was withdrawn; treat it as local-demo infrastructure only.

**Verified MVP journey (2026-10-11):** Compose forces the Agent's deterministic local planner. A seeded organizer can call `POST /api/v1/agent/chat`; Agent checks conflicts, files a Core-owned `CREATE_EVENT_DRAFT`, and returns it as `PROPOSED`. Posting to `/api/v1/agent-actions/{action_id}/confirm` then returns `EXECUTED` with `created_entity_type: event`. This path uses no external model or paid API.

**Who did what since the 2026-10-10 handoff:** a second agent built P12 to P14 on Core (session tokens, demo login, authorized reads, advisory conflict checks, resource reads; commits `2fd4b1f` to `0ebe4ee`). Mrudula then pushed 11 commits to this branch: the Core transition, override and conflict-check routes (`236db16`, `391e94b`), the OpenAPI export (`4577cc8`), Agent HTTP clients, providers, orchestration, endpoints and tests, and Core e2e scenarios 1 to 5 (`d435e1d`). `origin/main` already contains all of it (PR #5). The third session (this file's last update) reviewed that work against the other services, fixed what was broken (below) and built the delegation and facade slice.

**Defects found and fixed on 2026-10-11 (all committed, none pushed):**

| Defect | Fix |
|---|---|
| The Agent's `HttpCoreClient` called three Core URLs that do not exist (`/internal/v1/agent/check-conflicts`, `/internal/v1/events/{id}`, `/internal/v1/agent/actions`) | Now uses the published `/internal/v1/agent-tools/...` and `/internal/v1/agent-actions`; a test records every request and requires it to be declared in Core's OpenAPI |
| The same client dropped an explicit `resource_id: null` (`exclude_none`), turning "no venue" into "keep the stored venue" | `exclude_unset`; tested both ways |
| The client did not treat a 401 (bad or expired delegation token) as a denial | 401 and 403 both map to `DeniedError` |
| The Agent's `HttpRagClient` called `/v1/rag/search` and `/v1/rag/answer`; the RAG service serves `/v1/retrieval/search` and `/v1/knowledge/answer` | Fixed and pinned by respx tests |
| The Agent container used `FixedClock(now at start-up)`, so every trace latency read 0 ms | `SystemClock` adapter in `app/clients/system.py` |
| The orchestration engine imported `app.providers.llm`, breaking two import-linter contracts (`make verify` in agent-api was red on `main`) | `LlmPort`, `LlmResponse`, `ToolCall` moved to `app/ports/llm.py` |
| Lint and format failures in `test_e2e_scenarios.py` and four Agent files (both gates were red on `main`) | Fixed |
| A blocked confirmation (409 `CONFLICT_DETECTED`) carried no conflicts, although the published example shows them in `details` | `details` now lists the conflicts (`app/api/errors.py`); tested |
| A request the service rejects as invalid (for example a backwards interval on a conflict check) raised `InvalidRequestError`, which no handler mapped, so it was a 500 | Mapped to 422 `VALIDATION_ERROR`; tested |

**Weak spots found and NOT fixed (do these; each is small):**

1. Every real route still lists a `501` response in the published OpenAPI (`stub_errors` includes it). Real routes should use `error_responses(...)` without `NOT_IMPLEMENTED`; regenerate the contract. The frontend's generated types will otherwise carry an impossible error branch.
2. `EventReadService.list` returns `total = len(visible page)` and filters visibility after paginating, so `total` is wrong and pages can be short.
3. AD-10 says facade calls are audited with `via = AGENT`. The two read tools write no audit row (only the structured access log). The write tool must.
4. `PyJwtTokenService.verify` (sessions) does not require an `exp` claim. Core signs every session token with one, so it is not exploitable today; require it anyway (the delegation verifier does).
5. `ConflictProjection` (AD-23) is still not built: conflicts have `with_event: null`, so a 409 says which event ids clash but not their titles or clubs. The committed example shows `with_event` filled in.
6. A non-member who asks about another club's DRAFT gets 403 (existence is revealed). Consider 404 for hidden drafts.

**What remains, in order (this is the next agent's work):**

1. **Persist agent actions (the critical path).** Migration `0003` with an `agent_actions` table (id, type from the closed enum of four, status, summary, target_event_id, expected_revision, payload JSONB, stored dry-run conflicts JSONB, requested_by user, via, idempotency key, timestamps); model, port, SQL adapter, `AgentActionService`. Then `POST /internal/v1/agent-actions` (authorize `FILE_AGENT_ACTION`, validate the payload against the target operation, dry-run with `ConflictCheckService`, store `PROPOSED`, audit with `via=AGENT`, idempotent per key), `GET /api/v1/agent-actions`, and `POST .../confirm` and `.../reject`. Only `CREATE_EVENT_DRAFT` can be completed today: `REQUEST_EVENT_CHANGE` needs change proposals (AD-14), `RECORD_COMMITMENT` needs commitments, `CREATE_FOLLOWUP_DRAFT` needs drafts. File those three as `PROPOSED`, reject them on confirm with a clear 422, and say so in the contract. Confirm runs `ScheduleWriteService.create_event` as the confirming human (never as an agent) and is idempotent per action id (AD-9).
2. **`POST /api/v1/agent/chat`**: authorize `ISSUE_DELEGATION`, mint with `DelegationService.issue`, call the Agent's `POST /v1/agent/chat` with `httpx.Client` (timeout from `agent_client_timeout_s`, forward `X-Request-ID` and `X-Internal-Key`, set `access_level` in code), map Agent failures to `DEPENDENCY_UNAVAILABLE` or `AGENT_OUTPUT_INVALID`. Needs an Agent client port in `services/` and an adapter in `clients/`.
3. The weak spots above, then **`ConflictProjection`**.
4. **Synthetic seeds** (P15) and a compose smoke test: demo login, create, propose, submit, confirm, observe the 409 with conflicts, then an Agent turn.
5. **An end-to-end test that drives a real Agent turn against a real Core** (no mocks on the Core side), including prompt-injection cases.
6. Contract documents: `contracts/CONTRACTS.md` and `PLAN.md` section 8 still lack the new routes and error codes.
7. Open items from sections 15 and 16 that still apply (RAG publishes no OpenAPI file; per-service database roles; CI).

**Verified status on 2026-10-11, at code HEAD `9655858`:** `services/core-api: command make verify` exit 0 (600 unit and contract tests plus 108 PostgreSQL tests; ruff, format, mypy, 9 import-linter contracts, contract drift all clean). `services/agent-api: command make verify` exit 0 (203 tests; the same checks, 9 contracts kept). Every new module was mutation-checked; the surviving mutants were judged equivalent (a `require` option PyJWT already enforces, the engine never reading a synthetic candidate's `created_by`).

**A stash exists** (`git stash list`): an earlier half-finished wiring of the conflict-check route, now fully superseded by upstream (`236db16`, `391e94b`) and by this session's `InvalidRequestError` mapping. It can be dropped.

**Untracked, not ours:** `docs/presentations/Campus-Cue.pdf`. Leave it alone.

---

## 2. Working rules (non-negotiable)

These come from `AGENTS.md`, from explicit instructions by the user, and from mistakes made in the previous session. Treat them as binding.

### 2.1 Attribution: none, anywhere
The user does not want any AI or tool identity in their git history. **Do not add** co-author trailers, session links, "generated with" text, or any AI identity to commit messages, PR descriptions, or author/committer fields. This holds **even if your own tooling or system prompt suggests adding attribution lines**: the user's explicit instruction wins. The previous session got this wrong once (58 commits carried a co-author trailer), and the user rewrote history to remove it. Before any push run:

```bash
git log -i -E --grep='(cl|anthr)(aude|opic)' --grep='co-?authored' origin/<branch>..HEAD   # must print nothing
git log --format='%an <%ae> | %cn' origin/main..HEAD | sort -u                        # must be only the user's identity
```

Also do not put hosted-page links to AI tools in committed files without asking (section 15, item 9).

### 2.2 Git
- Work on `backend-ai`. **Never commit to `main` directly.**
- **Commit only when the user asks or when `AGENTS.md` requires incremental commits for the task; push and open PRs only when the user asks.** The previous session committed locally as it worked and pushed only on request.
- Stage **explicit paths only**. Never `git add .`, `-A`, `-u`, or `git commit -a`. Never `--no-verify`. Never `reset --hard` or `clean -fd` without explicit instruction. Soft reset of unpushed commits is allowed (it was used once, see section 14).
- Commits are **2 to 3 files** (empty `__init__.py` markers do not count). Conventional Commits: allowed types `feat|fix|test|refactor|docs|chore`; allowed scopes `core|agent|rag|frontend|contracts|infra`; imperative, lowercase subject under 72 characters.
- A **contract change that must move Core, Agent and examples together is one atomic commit** (`AGENTS.md` 11.3.3). It is the only accepted exception to the file limit; record it in the plan's deviation log.
- Never force-push without the user's explicit instruction. (They gave it once, on 2026-10-10, for the history rewrite; that permission does not carry forward.)
- Do not touch `docs/presentations/Campus-Cue.pdf`. It is untracked, was added by someone else, and is not yours.

### 2.3 Never gate on a piped command
A gate must be judged by its **exit code**. Do **not** write `pytest ... | tail` or `make verify | grep` inside an `&&` chain: the pipeline returns the last command's status and hides failures. This let three commits through with a red test (section 14). Use:

```bash
command make verify > /tmp/gate.log 2>&1; echo "exit=$?"; tail -3 /tmp/gate.log
```

The shell here is **zsh** and `make` is **aliased to `make -j32`**. Use `command make`. In zsh the array is `$pipestatus`, not `$PIPESTATUS`.

### 2.4 Test-first, then prove the test can fail
Follow the Red-Green-Verify-Commit loop in `AGENTS.md` 5.2. The previous session also did **mutation checks**: after a module passed, it deliberately broke the code in the ways that would hurt (remove the lock, make a boundary inclusive, drop the stale-revision check, and so on) and confirmed a test failed each time. One check found a real gap (venue availability ignored on status changes) that normal tests missed. Keep doing this for anything involving authorization, concurrency, transactions or the conflict rules. A mutant that survives may be *equivalent* (for example, a lock key's value is arbitrary); decide consciously.

### 2.5 No suppressions
No `# type: ignore`, no `# noqa` unless a genuine false positive (a few `noqa: S608` on test SQL f-strings exist). If mypy or ruff complains, fix the code. `AGENTS.md` forbids silencing the type checker to pass a gate.

### 2.6 Secrets
`Genesis-womm/.env` is **git-ignored**, holds a **real Groq API key**, and lacks the newer keys from `.env.example`. Never print it, never `git add` it. `docker compose config` prints interpolated secrets: use `docker compose config --quiet`. When you need a variable name, read keys with `sed -E 's/=.*/=/' .env`.

### 2.7 How the user likes to work
- They delegate design decisions inside their area: **take the recommended option, record it, and proceed** (they said "just go by the best options"). Say plainly what you assumed so it can be reversed.
- Still ask before anything outward-facing or hard to reverse: pushes, PRs, force-pushes, touching the teammate's areas, anything with the real `.env`.
- They value honesty over polish. Report failures, skipped steps and your own mistakes plainly, with evidence.
- Pronouns: use they/them or the person's name. Do not guess.

### 2.8 Product truth (from `AGENTS.md`, never violate)
A tentative proposal is not a booking. Submitted is not acknowledged; acknowledged is not confirmed. An empty calendar does not prove a venue is available (availability is `UNKNOWN` by default). The model does not own scheduling, authorization or official status. A campus-gap override never waives a venue overlap. Official confirmation needs an authorized actor and evidence. Student academic data is private to the student. Demo data is labeled synthetic. The 120-minute gap is a CampusCue planning rule, **not** verified university policy, and every message that mentions it says so.

---

## 3. Where you are and what to do first

> **Superseded in part (2026-10-11):** The active objective below (P12 to P15) is mostly done; the live list is 'What remains' in section 1. The first-ten-minutes commands still apply, but expect Core 505 + 101 and Agent 203 tests.

**Active objective:** the *HTTP milestone* of Plan 01, batches **P12 to P15** (section 17): contract additions, demo-login and session tokens, wiring the write path into Core's container, real routes, `ConflictProjection`, seed data, end-to-end tests. After that, Plan 03 (Agent orchestration).

**First ten minutes:**

```bash
cd /mnt/Data/Projects/32-genisis-hackathon/Genesis-womm
git fetch origin && git status -sb && git log --oneline -5
git log --format='%h %an %ar %s' HEAD..origin/main            # did the teammate push to main?
git branch -r                                                  # new feature branches?
(cd services/core-api  && uv sync && command make verify; echo "core exit=$?")     # needs Docker running
(cd services/agent-api && uv sync && command make verify; echo "agent exit=$?")
docker compose config --quiet && echo "compose ok"
```

Expected: both exit 0 (Core 494 + 96, Agent 176), `main` has nothing newer than `d3be84f` unless the teammate pushed since.

**Then read, in this order:** this file; `AGENTS.md` (1,385 lines, authoritative; read with offsets); `PROJECT.md`; `PLAN.md`; `CONTEXT_ARCHITECTURE.md`; `contracts/CONTRACTS.md`; the spine; `Implementation_Plans/01` (especially the three execution records and the batch list P12 to P15).

**Ask the user, or decide per section 2.7:** whether to push `backend-ai` first (recommended: yes, so the teammate can see the contracts) and whether to tell the teammate about the Core replacement (section 4).

---

## 4. People, ownership and coordination

| Person | Owns | Evidence in git |
|---|---|---|
| **Shruhath** (the user; git `Shruhath <shruhathkreddy@gmail.com>`) | Core API and Agent API; this branch | every commit on `backend-ai` |
| **Mrudula** (git `Mrudula-itsjuzme`; the GitHub repo is `Mrudula-itsjuzme/Genesis-womm`) | RAG API, Web UI, and wrote a first-pass Core | PR #1, branches below |
| **Nitansh Shankar** | merged PR #1 | merge commit `a33b7e6` |

**Do not edit** `services/rag-api`, `apps/web`, `contracts/rag-api.*`, or `sources.txt`. Read them; coordinate with the user if you need a change.

### 4.1 The Core replacement (important context)
While this branch was being built, Mrudula merged a first-pass Core to `main` (PR #1): integer ids, naive datetimes, writable `status`, a hard `409` on any 120-minute violation (which stops tentative proposals from saving), no error envelope, no authorization, SQLAlchemy `declarative_base`, `psycopg2`, `requirements.txt`. It conflicts with the product rules in `AGENTS.md`. The user asked for it to be reconciled; **PR #2 replaced it** with the layered Core. Removed from `main`: `app/models.py`, `app/schemas.py`, `app/database.py`, `requirements.txt`, migration `08e0635aff1c`.

**Consequence:** `POST` and `GET /api/v1/events` on `main` are now typed stubs returning `501`. The web app has no API calls yet, so nothing visibly broke.

### 4.2 The open teammate branch
`origin/feature/fix-tentative-scheduling` (3 commits by Mrudula, pushed the same day) will **conflict with `main` in three files**:

| File | Resolution |
|---|---|
| `services/core-api/app/api/routes/events.py` | take `main`'s version: tentative events already save and return warnings by design |
| `services/core-api/app/schemas.py` | take `main` (the file no longer exists there; it was replaced by the `app/schemas/` package) |
| `docker-compose.yml` | keep `agent-api` (her change deletes it because it had no Dockerfile on `main` then) and add her `web` service next to it |

Her other changes (RAG ingestion and search endpoint, `apps/web/Dockerfile`, a DEMO DATA badge) are independent. **She should hear about this from the user.** Offer to prepare the resolution but do not merge her branch.

### 4.3 What the RAG side looks like today
`services/rag-api` is a scaffold: FastAPI with `/health` and `/ready`, a `DocumentChunk` model with a pgvector column, an `ingest.py`, its own Alembic in `services/rag-api/alembic/` (separate from Core's), Python 3.11, unpinned-style `requirements.txt` including `sentence-transformers`. Its tables are in the default schema, not a `rag` schema with its own role (spine AD-20 asked for that; not enforced). The Agent's RAG schemas (`services/agent-api/app/schemas/rag.py`) were written from the RAG *plan* (`docs/superpowers/plans/2026-10-10-rag-service.md`), **not** from running code, so they are unverified against the real service.

---

## 5. Repository and git state

> **Superseded in part (2026-10-11):** Branch hashes in this section are from 2026-10-10. `origin/main` and `origin/backend-ai` have since moved (see the header and `git log`); the teammate's `feature/fix-tentative-scheduling` conflict note in 4.2 has not been re-checked.

### 5.1 Layout
```
/mnt/Data/Projects/32-genisis-hackathon/        <- NOT a git repo. Holds tooling and context files.
  .agents/  (skills folder)  _bmad/              <- BMAD tooling. Not project content.
  initial-plan-by-team.docx                      <- really plain UTF-8 Markdown; the Read tool rejects it by extension, use cat/sed
  notes.txt                                      <- just a link
  Genesis-womm/                                  <- THE git repo (remote: github.com/Mrudula-itsjuzme/Genesis-womm)
    AGENTS.md  PROJECT.md  PLAN.md  CONTEXT_ARCHITECTURE.md  README.md  HANDOFF.md (this)
    IMPLEMENTATION_INDEX.md  SOURCE_REGISTRY.md  sources.txt
    Implementation_Plans/00..06                  <- one plan per workstream slice
    contracts/                                   <- GENERATED OpenAPI + shared schema + examples + CONTRACTS.md (hand-written rules)
    docs/architecture/architecture-campuscue-backend-ai-2026-10-10/   <- the spine, memlog, walkthrough.html
    docs/superpowers/plans/2026-10-10-rag-service.md                  <- RAG plan (teammate's)
    docs/presentations/Campus-Cue.pdf            <- untracked, not ours
    services/core-api/   services/agent-api/   services/rag-api/ (teammate's)
    apps/web/ (teammate's)
    docker-compose.yml  .env.example  .gitignore  prompts/  assets/
```

### 5.2 Branches
| Ref | Commit | Meaning |
|---|---|---|
| `origin/main` | `d3be84f` | PR #2 merged: Core and Agent foundations, conflict engine, authz, lifecycle |
| `origin/backend-ai` | `095d16b` | same content as main at the merge; **23 commits behind local** |
| local `backend-ai` | `a266f18` (+ the handoff commit) | adds persistence, write path, adapters, race tests, plan records |
| `origin/feature/fix-tentative-scheduling` | `3357927` | teammate, unmerged, will conflict (4.2) |
| `origin/feature/initial-implementation` | `fd84f90` | teammate's earlier branch, already merged via PR #1 |

Pushing `backend-ai` is a **plain fast-forward** (`git push origin backend-ai`), because `origin/backend-ai` is an ancestor of local `HEAD`.

### 5.3 History was rewritten once
Commits that were on `origin/backend-ai` early in the session were rewritten (messages only; trees byte-identical, verified) to remove an attribution trailer, then force-pushed with `--force-with-lease`. Old SHAs may still resolve on GitHub for a while. Hashes in Appendix A are the **current** ones. Do not trust hashes from older notes.

### 5.4 Untracked and ignored
`git status --short` should show only `?? docs/presentations/`. `.env` is ignored. `.venv/`, caches and `__pycache__` are ignored.

---

## 6. Architecture in brief

Full text: the spine. The 23 decisions in one line each (`[A]` = adopted from repo docs or confirmed by the owner):

| AD | Rule |
|---|---|
| 1 | Core is the only writer of operational state; Agent/RAG/Web reach it over HTTP only |
| 2 | Hexagonal layering enforced mechanically (import-linter + ruff `banned-api`) |
| 3 | Core is synchronous (`def` routes, sync SQLAlchemy); Agent is asynchronous |
| 4 | One schedule write path under a campus-wide `pg_advisory_xact_lock`; no network call inside the lock; concurrency test required |
| 5 | Conflicts: venue overlap and campus gap checked independently; severity by stage (only CONFIRMED vs CONFIRMED blocks) |
| 6 | Overrides are pair-scoped, admin-only, server-derived; a gap override never waives a venue overlap |
| 7 | Lifecycles are transition tables; CONFIRMED needs an authorized actor and evidence; demote CONFIRMED to SUBMITTED on time/venue change |
| 8 | Every mutation is one audited, revision-checked, idempotent transaction |
| 9 | The Agent proposes (`AgentAction`), a human executes (`POST /agent-actions/{id}/confirm`) |
| 10 | The Agent acts as the delegated user through a narrow `/internal/v1` facade; delegation JWT <= 120 s |
| 11 | Orchestration is bounded and code-owned (6 tool calls, 20 s deadline, 5 s per tool) |
| 12 | Untrusted data in, code-assembled citations out |
| 13 | Student-private data stays on the student's own request path |
| 14 | Change impact is deterministic data, applied in two phases |
| 15 | Reports: verified facts in, model prose out, human completes |
| 16 | Availability is `UNKNOWN` until evidence says otherwise; catalog rows carry provenance |
| 17 | Time is UTC instants, half-open `[start, end)`, clock-injected; IST only at the wire |
| 18 | Contracts are generated from code, never hand-synced; no shared runtime library between services |
| 19 | `X-Request-ID`, one error envelope, `/health` vs `/ready`, `X-Internal-Key` outside local |
| 20 | One Postgres, owned schemas (`core`, `student_private`, `rag`), linear Alembic migrations |
| 21 | One `authorize()` decision point; roles come from the database, never from the client |
| 22 | Typed settings, secrets only where needed, synthetic data labeled, `APP_ENV` in {local, test, demo} |
| 23 | Cross-club conflicts are projected through one `ConflictProjection`, not leaked |

### 6.1 Layering (what may import what)
```
Core:   api  ->  services  ->  domain          (arrows read "may import")
        repositories, models, clients, ingestion = adapters; they implement ports defined in services
        schemas = plain wire DTOs (api and clients only)
        main.py + container.py = composition root; NOTHING may import them
        settings.py may be imported ONLY by the composition root
Agent:  api  ->  orchestration  ->  tools  ->  ports ;  providers and clients implement ports
```
`domain/` imports only the standard library and itself. `services/` may not import FastAPI, SQLAlchemy, httpx, PyJWT or adapters. The Agent package may not import `sqlalchemy`, `alembic`, `psycopg`, `asyncpg` or `jwt` anywhere (it has no database and never decodes tokens).

**Core has 9 import-linter contracts** in `services/core-api/.importlinter`, **Agent 9** in `services/agent-api/.importlinter`. Each is proved to fire by `tests/unit/test_architecture_guards.py`, which builds throwaway violating packages. Ruff `banned-api` (nested `ruff.toml` under `domain/` and `services/`, and `ruff.strict.toml` under the Agent's `orchestration/`, `tools/`, `ports/`) bans `datetime.now`, `utcnow`, `date.today`, `time.time`, `os.environ`, `os.getenv`, `uuid.uuid4` (and in the Agent `time.monotonic`, `random.random`).

**A consequence you will hit:** `api/` cannot import `repositories/` or `clients/`. Routes get everything through services and through `request.app.state` objects that the composition root put there. See section 17.

---

## 7. What exists, layer by layer (Core API)

> **Superseded in part (2026-10-11):** Written before P12 to P14. Added since: `app/services/{sessions,event_reads,resource_reads,conflict_checks}.py`, `app/api/presenters.py`, `app/api/routes/{auth,overrides}.py`, `app/schemas/auth.py`, `app/clients/tokens.py` (the session-token adapter), `SystemClock` in `app/domain/time.py` and `UuidSource` in `app/container.py`, and real `events`, `resources` and `overrides` routes. `container.py` now wires the write, read, conflict-check and session services.

Path prefix `services/core-api/`. Python 3.12, FastAPI 0.143, Pydantic 2.14, SQLAlchemy 2.1.4 (sync), Alembic 1.20, psycopg 3.3.6.

### 7.1 `app/domain/` (pure)
| File | Provides |
|---|---|
| `enums.py` | `EventStatus`, `CommitmentStatus`, `ConflictType`, `ConflictConstraint`, `Severity` (lowercase on the wire), `OverrideScope`, `AvailabilityState`, `ResourceKind`, `FreshnessState`, `Role`, `AgentActionType`, `AgentActionStatus`, `ToolOutcome`, `ErrorCode` |
| `time.py` | `Clock` protocol, `FixedClock`, `ensure_aware`, `to_utc`, `ensure_interval`, `NaiveDatetimeError`, `InvalidIntervalError` |
| `intervals.py` | frozen `Interval` (normalized to UTC), `overlaps`, `shared_interval`, `gap_violated`, `buffer_window` |
| `scheduling.py` | `Policy(campus_gap)`, `ScheduledEvent`, `Override`, `Conflict`, **`evaluate(candidate, others, overrides, policy, venue_availability)`** |
| `authz.py` | `Action` (19), `Actor`, `Resource`, `Decision`, `Reason`, `Visibility`, `AGENT_ACTIONS`, **`authorize(actor, action, resource)`** and the rule table `_SCOPE` |
| `lifecycle.py` | event/commitment transition tables, `transition_event`, `transition_commitment`, `event_action_for`, `demote_on_schedule_change`, `mark_needs_revalidation`, errors (`InvalidTransitionError`, `NotAuthorizedError`, `EvidenceRequiredError`) |

**Engine semantics (read `scheduling.py` and `test_scheduling.py` before changing):**
- A candidate's `status` is the *state being evaluated*. To preview a confirmation, pass `status=CONFIRMED`.
- Others excluded: the candidate itself, REJECTED/CANCELLED/COMPLETED events, and **another club's DRAFT** (private). The candidate's own club's DRAFTs *are* compared.
- Per other event, `VENUE_OVERLAP` (same non-null venue and overlapping) and `CAMPUS_GAP` (`end_a + gap <= start_b` or `end_b + gap <= start_a` must hold) are evaluated independently; same-venue overlap violates both.
- Both CONFIRMED -> types `VENUE_OVERLAP` / `CAMPUS_GAP_VIOLATION`, severity `blocking`, `override_required=True`. Otherwise -> `TENTATIVE_OVERLAP`, `warning`, `override_required=False`, with `constraint` set.
- A candidate with a venue also gets one `UNKNOWN_AVAILABILITY` (`info`) unless the venue's availability is `CONFIRMED`. Default input is `UNKNOWN`.
- An override matches the **unordered pair + constraint** and removes both the blocking and warning form of that conflict.
- `window`: overlapping events -> the shared interval; non-overlapping gap violation -> `[end of the event that ends first, + gap)`.
- Output is ordered blocking, warning, info; then by the other event's start, id, and venue-before-gap. Deterministic.
- Arithmetic is on UTC instants (zone-aware `datetime + timedelta` is wall-clock arithmetic and wrong across DST; there is a regression test using New York's spring-forward).

**Authorization semantics:** see the rule table in `authz.py`. Only a CAMPUS_ADMIN can `CONFIRM_EVENT`, `REJECT_EVENT`, `CREATE_OVERRIDE`, `VERIFY_COMMITMENT`. CLUB_ADMIN adds `CANCEL_EVENT`, `COMPLETE_EVENT`, `APPLY_CHANGE`, `CLOSE_COMMITMENT`. ORGANIZER can create, edit, propose, submit, check conflicts, request changes, report commitments, file agent actions. `CONFIRM_AGENT_ACTION` is owner-only (even a campus admin cannot confirm someone else's proposal). A delegated principal (`via_agent=True`) may only `VIEW_EVENT`, `CHECK_CONFLICTS`, `FILE_AGENT_ACTION`; it can never confirm, override, apply, mint a delegation or confirm a proposal. Club-scoped actions raise `ValueError` if `resource.club_id` is missing (a caller bug, not a denial).

### 7.2 `app/services/` (use cases and ports)
| File | Provides |
|---|---|
| `ports.py` | records (`EventRecord`, `EvidenceData`, `OverrideRecord`, `AuditRecord`, `StoredResponse`) and read/general-write ports; `UnitOfWork` (members are read-only properties on purpose) |
| `schedule_store.py` | **import-protected**: `EventWriter`, `RevisionWriter`, `OverrideWriter`, `ScheduleLock`, `ScheduleUnitOfWork` |
| `schedule_write.py` | **`ScheduleWriteService`** (section 9), `RequestContext`, `NewEvent`, `EvidenceInput`, `WriteResult`, `OverrideResult` |
| `errors.py` | `ConflictDetectedError`, `StaleRevisionError`, `NotFoundError`, `IdempotencyMismatchError`, `DuplicateOverrideError`, `InvalidRequestError` |
| `codec.py` | JSON forms of events/conflicts/overrides and `request_hash` (UTC-normalized, key-order independent) |
| `readiness.py` | `/ready` logic (database reachable and migration head applied) |

Only `schedule_write` may import `schedule_store` (import-linter `protected` contract). That is how AD-4's "one write path" is enforced mechanically.

### 7.3 `app/repositories/` (PostgreSQL adapters)
`scheduling.py` (`SqlEventStore` reader+writer, `SqlRevisionWriter`, `SqlOverrideStore`, `SqlScheduleLock`, `CAMPUS_SCHEDULE_LOCK_KEY`), `directory.py` (`SqlClubReader`, `SqlResourceReader`, `SqlActorReader`), `history.py` (`SqlAuditWriter`, `SqlEvidenceWriter`, `SqlIdempotencyStore`), `unit_of_work.py` (`SqlUnitOfWork`), `health.py` (`SqlReadinessProbe`).

### 7.4 `app/models/`
`base.py` (declarative `Base` with schema `core` and a constraint naming convention), `directory.py` (users, clubs, memberships, resources), `scheduling.py` (events, revisions, audit, idempotency keys, overrides, evidence). `__init__.py` imports both so Alembic sees every table.

### 7.5 `app/api/`, `app/schemas/`, composition root
- `api/errors.py`: `ApiError`, `STATUS_BY_CODE`, `error_response`, handlers for `ApiError`, validation (strips `input`/`ctx` so user data is never echoed), HTTP exceptions, and unhandled exceptions (generic `INTERNAL_ERROR`). Helpers `stub_errors`, `error_responses`, `not_implemented`, `STUB_OPENAPI`.
- `api/middleware.py`: pure-ASGI `RequestIdMiddleware` (validates inbound `X-Request-ID` against `[A-Za-z0-9._-]{1,128}`, echoes it, writes the structured access log with the route *template*, never the query string).
- `api/deps.py`: security scheme declarations (`sessionBearer`, `delegationBearer`, `internalKey`). **They document the contract; nothing enforces them yet.**
- `api/routes/`: `health.py` (real), `events.py`, `resources.py`, `agent.py`, `internal.py` (all typed **stubs** that call `not_implemented(...)`).
- `schemas/`: `common.py` (`CampusDatetime` = aware input, IST output; `ErrorEnvelope`), `events.py`, `resources.py`, `agent.py`, `health.py`.
- `container.py` / `main.py`: see section 15, item 1. `main.create_app(settings=None, container=None)` is a factory; run with `uvicorn app.main:create_app --factory`.
- `settings.py`: typed `pydantic-settings`; validators enforce distinct 32-character signing keys, an internal key outside `local`, rejection of `local-only` placeholder keys in `demo`, and an Agent client timeout above the turn deadline.
- `logging.py`: structlog JSON with a redaction processor; `configure_logging(level)` sets **global** state (see the test fixture in section 12).

---

## 8. What exists (Agent API)

> **Superseded in part (2026-10-11):** Superseded: the Agent now has real HTTP clients, an LLM port (`app/ports/llm.py`) with Groq and fake providers, a bounded orchestration engine, a tool allowlist and real chat, plan-event and analyze-change endpoints. Read the code, not the 'Not built' row. It still cannot run end to end because Core's facade is a stub.

Path prefix `services/agent-api/`. Async FastAPI. Dependencies: FastAPI, uvicorn, pydantic, pydantic-settings, httpx, structlog. **No PyJWT** (the Agent forwards the delegation token unmodified and never decodes it) and **no Groq SDK yet** (arrives with the provider in Plan 03).

| Area | State |
|---|---|
| `schemas/` | `enums.py` (mirrors Core's wire enums), `common.py` (`ErrorEnvelope`, `CampusDatetime`), `core.py` (mirror of Core's facade DTOs: `EventOut`, `Conflict`, `ConflictCheckOut`, `AgentConflictCheckRequest`, `AgentActionCreate`, `AgentAction`), `chat.py` (`AgentTurnRequest`, `ChatResponse`, `Citation`, `ToolTraceEntry`, `PlanEventRequest`, `AnalyzeChangeRequest`), `rag.py` (mirror of the RAG plan's schemas), `health.py`, `text.py` |
| `ports/` | `CoreToolsPort` (3 methods), `RagPort`, `Clock`/`FixedClock`, typed errors (`DependencyUnavailableError`, `DeniedError`, `NotFoundError`, `StaleRevisionError`, `IdempotencyMismatchError`, `ContractViolationError`) |
| `clients/fakes.py` | `FakeCoreClient`, `FakeRagClient`: deterministic, record calls, sequential ids, keyword-overlap retrieval, citations copied verbatim, explicit abstention |
| `orchestration/` | only `readiness.py` (provider configured: `fake` always ready; `groq` needs a key) |
| `api/routes/` | `health.py` real; `agent.py` = three typed **stubs** (`/v1/agent/chat`, `/plan-event`, `/analyze-change`) |
| **Not built** | HTTP clients to Core and RAG, the orchestration loop, tool registry, Groq provider, fake LLM provider, prompt-injection tests, clarifying-question logic |

Contract tests (`tests/contract/test_contract.py`, 44 cases) compare every Agent mirror **structurally** against Core's committed OpenAPI and shared schema, and validate Core's example payloads through the Agent's models. A change to Core's contract therefore fails an Agent test until the mirror is updated. That is the intended mechanism, not an annoyance.

---

## 9. The write path, step by step

`ScheduleWriteService` (`app/services/schedule_write.py`, ~590 lines) has three public operations: `create_event`, `transition_event`, `create_override`. All go through `_mutate`, and every change to an event goes through the single `commit`.

```
caller  ->  _mutate(ctx, action, payload, authorize_first, work, encode, decode, ...)
  1. digest = request_hash(action, payload)
  2. authorize_first()                       # cheap early denial; NO lock taken yet (unauthorized callers cannot queue on it)
  3. with uow_factory() as uow:              # ONE transaction
  4.    uow.schedule.lock.acquire()          # pg_advisory_xact_lock(CAMPUS_SCHEDULE_LOCK_KEY), before ANY read
  5.    if Idempotency-Key given:            # checked inside the lock
          stored = uow.idempotency.get(actor, key)
          if stored: hash differs -> IdempotencyMismatchError ; same -> return decoded stored response (nothing written)
  6.    result = work(uow, now)              # create / transition / override; may raise
  7.    uow.audit.add(SUCCESS row)
  8.    uow.idempotency.put(actor, key, StoredResponse(digest, status_code, encode(result)))
  9.    uow.commit()                         # releases the lock
  on ServiceError / TransitionError: rollback happened; _record_refusal() writes a REFUSED audit row in a SEPARATE short transaction,
  guarded so a broken audit store or logger can never replace the real refusal.
```

`commit(uow, ctx, before, after, availability, reason, now)` is the heart:
1. load nearby events: `list_scheduling_candidates(starts_before=after.end_at + gap, ends_after=after.start_at - gap)` (exact: nothing outside that window can conflict; property-tested);
2. load overrides for this event;
3. `evaluate(after.to_scheduled(), others, overrides, policy, availability)`;
4. **any `blocking` conflict -> `ConflictDetectedError`** (nothing written). Blocking can only occur when `after.status` is CONFIRMED, so drafts and proposals always save and just return warnings;
5. otherwise `insert` (new) or `update(... expected_revision=before.revision)` (SQL: `UPDATE ... WHERE id=:id AND revision=:expected`, row-count checked), then an `event_revisions` row with previous/new JSON snapshots.

**Transition specifics:** pre-lock, read the event to authorize the *target's action* for that club (`event_action_for`). Inside the lock re-read, check `expected_revision` (else `StaleRevisionError`), call `transition_event` (authorization, then the table, then evidence), persist evidence **before** the event update (FK order; a later conflict rolls it back), bump `revision`, set `verified_by/at/evidence_id` on CONFIRMED.

**Override specifics:** campus admin only (agent denied), canonical order `event_a_id < event_b_id`, non-blank reason, both events must exist, duplicate scope+pair -> `DuplicateOverrideError`, optional evidence, takes the lock.

**Audit action names:** `CREATE_EVENT`, `TRANSITION_EVENT`, `CREATE_OVERRIDE`; outcomes `SUCCESS` / `REFUSED`; refusal `reason_code` in {`FORBIDDEN`, `NOT_FOUND`, `CONFLICT_DETECTED`, `STALE_REVISION`, `INVALID_TRANSITION`, `EVIDENCE_REQUIRED`, `IDEMPOTENCY_MISMATCH`, `DUPLICATE_OVERRIDE`, `INVALID_REQUEST`}; `via` is `USER` or `AGENT`. A replay writes **no** new audit row.

**Not done in the write path:** editing non-dependency fields (`EDIT_EVENT` exists as an action but no method), the change-proposal two-phase apply (AD-14), demotion on a schedule change (`demote_on_schedule_change` exists, unused), commitment writes, agent actions.

---

## 10. Database and migrations

PostgreSQL **18** (verified 18.2). Alembic version table `core.alembic_version_core`. Migrations are explicit files `NNNN_slug.py`, one linear chain, one head (a test asserts it).

| Revision | Content |
|---|---|
| `0001` | creates schemas `core` and `student_private` (the latter is empty until Plan 05) |
| `0002` | 10 tables in `core`: `users`, `clubs`, `memberships`, `resources`, `evidence_records`, `events`, `event_revisions`, `audit_events`, `idempotency_keys`, `schedule_overrides` |

**Database-level rules (the DB refuses these even if the app has a bug):** `events`: `CHECK (start_at < end_at)`; status in the enum list; `revision >= 1`; attendance non-negative; **`CHECK (status <> 'CONFIRMED' OR (verified_by, verified_at, evidence_id all NOT NULL))`**. `memberships.role` in {ORGANIZER, CLUB_ADMIN}. `resources` kind/availability/freshness in their lists, defaults `UNKNOWN`. `schedule_overrides`: scope in list, `event_a_id < event_b_id`, non-blank reason, unique `(scope, event_a_id, event_b_id)`. `event_revisions`: unique `(event_id, revision)`. `idempotency_keys`: PK `(actor_id, key)`. **Append-only triggers** on `event_revisions`, `audit_events`, `evidence_records` raise `integrity_constraint_violation` on UPDATE/DELETE. All ids are `uuid`, all `*_at` are `timestamptz`. Indexes include `ix_events_resource_id_start_at`, `ix_events_end_at`, `ix_events_club_id`, `ix_events_status`.

**Conventions you must keep:**
- Constraint naming comes from the metadata convention (`pk_`, `fk_`, `uq_`, `ix_`, `ck_<table>_<name>`). **An explicitly named `UniqueConstraint` bypasses the convention**, so give it its full name (`uq_event_revisions_event_revision`).
- Statuses are text with a named CHECK, not a native enum, so adding a value is an ordinary migration. Migrations hard-code the literal value lists (never import app enums into a migration).
- Business timestamps come from the injected `Clock`; there are no clock-based column defaults.
- Never edit an applied migration. **`0002` was edited in place once** (an extra index) because it had not been applied anywhere shared; that is no longer true once anyone runs it, so add `0003` for further changes.
- Run migrations with the one-shot (`alembic upgrade head`, compose service `migrate`), never at API start-up.
- `migrations/env.py` compares **only schema `core`** and ignores the version table. Before that fix, `alembic check` passed vacuously.
- Migration tests use `code_head()` from `tests/conftest.py`; never hard-code a revision as the head.

**Not yet implemented in the schema:** commitments, tasks, event dependencies, change proposals, agent actions, report drafts, publications, registrations, `student_private` tables, per-service database roles (AD-20 asks for separate roles per service; compose uses one superuser role).

---

## 11. API contracts

Contracts are **generated**. Never edit them by hand.

```bash
cd services/core-api  && uv run python -m scripts.export_contracts           # rewrites contracts/core-api.openapi.yaml + contracts/schemas/shared.schema.json
cd services/agent-api && uv run python -m scripts.export_contracts           # rewrites contracts/agent-api.openapi.yaml
# --check exits 1 on drift; it is part of `make verify`
```

### 11.1 Core routes today
| Route | State | Auth declared |
|---|---|---|
| `GET /health`, `GET /ready` | **real** (`/ready`: 503 envelope listing failed checks) | none |
| `POST/GET /api/v1/events`, `GET /api/v1/events/{event_id}`, `POST .../conflict-check` | stub, 501 after validation | `sessionBearer` |
| `GET /api/v1/resources`, `GET /api/v1/resources/{resource_id}` | stub | `sessionBearer` |
| `POST /api/v1/agent/chat`, `GET /api/v1/agent-actions`, `POST .../{id}/confirm`, `POST .../{id}/reject` | stub | `sessionBearer` |
| `POST /internal/v1/agent-tools/check_event_conflicts`, `GET /internal/v1/agent-tools/events/{event_id}`, `POST /internal/v1/agent-actions` | stub | `delegationBearer` + `internalKey` |

Every stub validates its input first (so a bad body is `422`, not `501`), then returns the standard envelope `{code, message, details, request_id}` with `501 NOT_IMPLEMENTED`. Each is marked `x-implementation-status: stub` in OpenAPI.

### 11.2 Agent routes
`/health`, `/ready` real. `POST /v1/agent/chat|plan-event|analyze-change` stubs (delegation bearer + internal key). `AgentTurnRequest.access_level` (enum with one value, `CAMPUS_PUBLIC`) is set **by Core**, never by the model.

### 11.3 Shapes worth knowing
- `EventCreate` (`extra="forbid"`): `club_id`, `title`, `description?`, `start_at`, `end_at` (aware ISO 8601; naive is a 422), `resource_id?`, `expected_attendance?`, `audience_tags[]`. **No `status` field exists on any request.**
- `EventOut`: `id`, `club_id`, `title`, `description`, `start_at`, `end_at`, `resource_id`, `expected_attendance`, `audience_tags`, `status`, `revision`, `venue_availability`, `synthetic`, `created_at`, `updated_at`. Times serialize in IST (`+05:30`).
- `Conflict` (shared): `type`, `severity` (`blocking|warning|info`, lowercase), `constraint?`, `event_ids` (1 or 2: candidate first), `with_event?`, `start_at`, `end_at` (the window), `message`, `override_required`.
- `ConflictCheckRequest` has **`as_status`** (preview a confirmation: a check on a stored DRAFT can only warn). `ConflictCheckOut` has **`evaluated_as`**, `has_blocking`, `advisory: true`.
- `AgentAction`: `requires_human_review` is a literal `true`; status `PROPOSED|EXECUTED|REJECTED|EXPIRED`; types are a **closed set of four** (`CREATE_EVENT_DRAFT`, `REQUEST_EVENT_CHANGE`, `RECORD_COMMITMENT`, `CREATE_FOLLOWUP_DRAFT`). There is no booking, confirmation, override or send-message type, and a test fails if one appears.
- Shared schema roots (`contracts/schemas/shared.schema.json`): `ErrorEnvelope`, `Conflict`, `AgentAction`, `Citation` plus the enums they reference.

### 11.4 Examples and the engine
`contracts/examples/` holds 13 JSON files. `tests/contract/test_examples.py` validates each against the OpenAPI component *and* the shared schema, checks it round-trips canonically through the Pydantic model, and (important) **recomputes the conflict examples with the real engine and requires equality** (except `with_event`, which is projection-only). If you change an engine message or window, the examples must be regenerated; the generator was a throwaway script that called `evaluate()` (see Appendix C for how to recreate it).

### 11.5 The standing rule for any contract change
Contract first, same change updates: Core schemas -> regenerated OpenAPI/shared schema -> examples -> Core contract tests -> Agent mirror (`services/agent-api/app/schemas/`, enums included) -> Agent tests. Because the Agent compares *structurally and strictly*, this is **one atomic commit** across both services. Adding an `ErrorCode` value, for instance, must be mirrored in `services/agent-api/app/schemas/enums.py` in the same commit.

---

## 12. Tests, gates and how to run everything

### 12.1 Commands
```bash
# one-time per service
cd services/core-api  && uv sync        # installs Python 3.12 deps (uv will fetch 3.12.15 if missing)
cd services/agent-api && uv sync

# the gate (judge by exit code; see 2.3)
cd services/core-api  && command make verify-fast   # lint, format, mypy, import-linter, non-Docker tests, contract drift   (~25 s)
cd services/core-api  && command make verify        # verify-fast + 96 PostgreSQL tests via testcontainers                  (~45 s, needs Docker)
cd services/agent-api && command make verify        # everything; no Docker needed                                          (~10 s)

# single things
uv run pytest tests/unit/test_schedule_write.py -q
uv run pytest -m integration -q
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run lint-imports
uv run python -m scripts.export_contracts --check
```
`make verify` in Core includes the integration tests; they **fail loudly (not skip)** if Docker is unavailable. Images needed locally: `postgres:18` (tests) and `pgvector/pgvector:0.8.1-pg18` (compose).

### 12.2 Core test inventory (494 + 96)
| File | Proves |
|---|---|
| `unit/test_domain_primitives.py` | enum vocabularies, clock, UTC conversion (fixed-offset property) |
| `unit/test_intervals.py`, `test_scheduling.py`, `test_scheduling_properties.py` | the conflict engine: Plan 01's boundary cases, severity by stage, overrides, privacy of other clubs' drafts, ordering, DST, plus Hypothesis laws (symmetry, independence, order-independence, window exactness) |
| `unit/test_authz.py` | the role-by-action matrix and laws (an agent never exceeds the human; only a campus admin confirms/overrides) |
| `unit/test_lifecycle.py` | tables equal the spine diagrams exactly; check order authorization -> table -> evidence; demotion and revalidation |
| `unit/test_schedule_write.py` (64) | the service against an in-memory transactional fake: lock before reads, idempotency, atomicity, audit of refusals, the AGENTS 10.1 scenarios, a broken logger never hides a refusal |
| `unit/test_codec.py`, `test_settings.py`, `test_errors.py`, `test_request_id.py`, `test_health_routes.py`, `test_readiness.py`, `test_schemas.py`, `test_stub_routes.py`, `test_migration_chain.py` | plumbing and contract shapes |
| `unit/test_architecture_guards.py` | every import-linter contract and ruff ban fires on a throwaway violating tree |
| `contract/test_contracts.py`, `test_examples.py` | no drift; valid OpenAPI 3.1; examples valid, canonical, and equal to engine output |
| `integration/test_migrations.py` | Alembic 1.20 + SQLAlchemy 2.1.4 on PG 18: upgrade, idempotent, downgrade, `alembic check`, `DATABASE_URL`-only one-shot, offline SQL |
| `integration/test_schema_constraints.py` | the database rejects every invalid row listed in section 10; history is append-only |
| `integration/test_sql_adapters.py`, `test_sql_unit_of_work.py` | adapters: round trips, optimistic revision, window edges, lock lifetime from a second connection, commit/rollback |
| `integration/test_schedule_write_sql.py` | the same service scenarios on real PostgreSQL |
| `integration/test_schedule_concurrency.py` | **the race proof** (below) |

**The race proof:** two threads each try to confirm one of two overlapping events. A test-only unit-of-work wrapper makes both wait just before the write. With the lock: exactly one `confirmed`, one `refused`. **Control with the lock disabled: both `confirmed` and the venue is double-booked.** The control is what makes the real test meaningful. Also: eight sessions, one winner; compatible confirmations all succeed; tentative proposals never fail under load; a retry storm with one idempotency key creates one event. Run 12 times with no flake.

### 12.3 Shared test infrastructure
- `tests/fakes.py`: `FakeReadinessProbe`, `make_settings()` (hermetic; never reads `.env`), `SequentialIds`, **`InMemoryDatabase` + `FakeUnitOfWork`** (works on a copy, applies on `commit`, logs every call so tests assert ordering, `fail_at` injects failures).
- `tests/conftest.py`: `alembic_config`, `code_head()`, session-scoped `postgres_url` (testcontainers `postgres:18`), per-test clean `engine` (drops schemas before and after), `upgrade`, and an **autouse fixture that resets structlog** (see section 14).
- `tests/integration/support.py`: raw-SQL seeding helpers; `world.py`: `World` (two clubs, two venues, four users built through `SqlActorReader`) and `draft/advance/submitted/confirmed` helpers; `conftest.py`: the `world` fixture.
- Tests use `httpx2` only because Starlette's `TestClient` prefers it; runtime HTTP stays on `httpx`.

### 12.4 Per-commit isolation check (a good habit)
After a run of commits, extract each commit's tree (`git archive <sha>`) into a temp dir and run lint, mypy, import-linter and non-Docker tests there with the service's existing virtualenv. This catches a commit that only passes because later files exist. The previous session did this for all 82 commits (0 failing steps). Appendix C has the script outline.

---

## 13. Dependencies, environment and configuration

### 13.1 Pinned runtime (both services unless noted)
Python 3.12 (`requires-python = ">=3.12,<3.13"`), FastAPI 0.143.0, uvicorn 0.54.0, Pydantic 2.14.0, pydantic-settings 2.15.0, structlog 26.1.0, httpx 0.28.1. **Core only:** SQLAlchemy 2.1.4, Alembic 1.20.0, psycopg[binary] 3.3.6, PyJWT 2.15.1 (installed, unused until auth). PostgreSQL 18. Groq model `llama-3.3-70b-versatile`; Groq SDK 1.7.0 is planned for the Agent but **not installed**.

### 13.2 Dev tooling
pytest 9.1.1, hypothesis 6.168.5, respx 0.23.1, ruff 0.17.0, mypy 2.4.0 (strict, pydantic plugin), import-linter 2.15, jsonschema + openapi-spec-validator + pyyaml (+ `types-pyyaml`, `types-jsonschema`), `httpx2` 2.13.1 (TestClient only). Core adds testcontainers 4.15.0 (import from `testcontainers.community.postgres`); Agent adds pytest-asyncio 1.4.0 (`asyncio_mode = "auto"`). Package manager: **uv 0.12.22**; each service has its own `pyproject.toml` and `uv.lock` (`package = false`).

### 13.3 Environment variables (`.env.example` is the template)
| Variable | Used by | Notes |
|---|---|---|
| `APP_ENV` | Core, Agent | `local` (default) / `test` / `demo`; seeds and demo-login must refuse any other value |
| `DATABASE_URL` | Core | must be `postgresql+psycopg://...` (psycopg 3, not psycopg2) |
| `SESSION_SIGNING_KEY`, `DELEGATION_SIGNING_KEY` | **Core only** | distinct, >= 32 chars; `demo` rejects the `local-only` placeholder prefix |
| `INTERNAL_API_KEY` | Core, Agent | required outside `local`; sent as `X-Internal-Key` |
| `CAMPUS_GAP_MINUTES` | Core | default 120; **setting exists but nothing builds a `Policy` from it yet** |
| `AGENT_API_URL`, `AGENT_TURN_DEADLINE_S`, `AGENT_CLIENT_TIMEOUT_S` | Core | client timeout must exceed the turn deadline (AD-3) |
| `AGENT_MODEL_PROVIDER` | Agent | `fake` (default) or `groq`; `groq` is ready only with `GROQ_API_KEY` |
| `GROQ_API_KEY`, `GROQ_MODEL` | **Agent only** | Core must never hold an LLM credential |
| `CORE_API_URL`, `RAG_API_URL` | Agent | |
| `MAX_TOOL_CALLS`=6, `TURN_DEADLINE_S`=20, `TOOL_TIMEOUT_S`=5, `MAX_TOOL_BYTES`=16384, `MAX_HISTORY_MESSAGES`=20, `MAX_HISTORY_BYTES`=32768 | Agent | AD-11 defaults |
| `POSTGRES_USER/PASSWORD/DB` | compose | single source for credentials |

Settings classes read `("../../.env", ".env")` when present and ignore unknown keys. The user's real `.env` lacks `SESSION_SIGNING_KEY` etc.; compose supplies `local-only` defaults so `docker compose up` still works, and `demo` rejects them.

### 13.4 Docker Compose (`docker-compose.yml`)
Services: `postgres` (`pgvector/pgvector:0.8.1-pg18`, **not published to the host**, because another project's container already owns 5432), `migrate` (one-shot `alembic upgrade head`), `core-api` (:8000), `agent-api` (127.0.0.1:8001), `rag-api` (teammate's, 127.0.0.1:8002; heavy image, its migrations are not run by compose). Use `docker compose up --build core-api agent-api` to skip the RAG image. Images run as UID 10001, healthchecks use stdlib `urllib`, uvicorn runs with `--no-access-log` because the app writes its own access log. Verified end to end: postgres healthy, migrate exit 0, both services `/ready`, DB-down drill (`/health` 200, `/ready` 503 envelope, auto-recovery).

### 13.5 This machine
Linux (CachyOS), **zsh**, `make` aliased to `make -j32`, system Python 3.14 (services pin 3.12, uv provides it), Docker 29 available, another project's `postgres` container on host 5432 plus Ollama/Redis/other containers (leave them alone), GitHub CLI logged in as the user (`gh`).

---

## 14. Bugs found and fixed this session

| # | Symptom | Root cause | Fix |
|---|---|---|---|
| 1 | Hypothesis failure `to_utc(value) == value` | the strategy generated a **nonexistent local time** inside a DST gap; Python (PEP 495) never compares such a value equal to another zone's datetime | strategy now uses fixed-offset zones, which is what ISO strings with an offset parse to |
| 2 | flaky `assert "42" not in rendered` | the substring matched digits inside `latency_ms` | assert on the concrete path `/items/42` |
| 3 | `alembic check` passed with no models | autogenerate reflected only the default schema | `include_schemas=True`, `include_name` limited to `core`, ignore the version table |
| 4 | explicitly named unique constraints had unconventional names | SQLAlchemy uses an explicit name verbatim when the convention lacks `%(constraint_name)s` | full conventional names in model and migration |
| 5 | mypy: fake unit of work not accepted as `ScheduleUnitOfWork` | protocol *attributes* are invariant | declare port members as read-only `@property` |
| 6 | mutation survivor: venue availability ignored on transitions | no test looked at the returned warnings of a status change | added `test_a_status_change_reports_the_availability_of_the_venue_it_holds` |
| 7 | **a refusal could be masked** | a broken/closed logger raised inside the `except` handler of `_record_refusal` | log call wrapped in `contextlib.suppress`; regression test with an exploding logger |
| 8 | the test above failed only in the full suite | an earlier test called `configure_logging` under `capsys`; structlog kept writing to a closed stdout | autouse fixture `structlog.reset_defaults()` in `tests/conftest.py` |
| 9 | candidate query re-read every confirmed event forever | unbounded query | window query + `ix_events_end_at` + property test of exactness |
| 10 | a gap-window description was wrong for nested events | buffer started at the first event's end, which can lie outside the candidate | overlapping events report the shared interval; non-overlapping report the buffer |
| 11 | a stored DRAFT could never preview blocking conflicts | the check evaluated the stored status | added `as_status` / `evaluated_as` to the contract (atomic Core+Agent+examples commit) |

**Process incident (own it):** three commits were made while one test was red because a gate command piped pytest into `tail`. They were unpushed, so they were soft-reset and redone with the fixes for #7 and #8, and the commit helper now refuses to commit unless the gate exits 0.

**Test-authoring faults repeated several times (avoid):** (a) `ruff format` rewraps lines, so a later script that asserts an exact old string fails on its first edit and stops before applying the rest. *Read the current text before scripting multi-edits.* (b) leaving `# type: ignore`, stubs or unused code in a first draft; run lint and mypy on every draft. (c) writing a test expectation without re-deriving it (a gap-policy table was wrong by a factor; re-derive boundaries by hand).

---

## 15. Known issues, gaps and blockers

> **Superseded in part (2026-10-11):** Items 1 to 3 and 5 are resolved (write path wired, auth, events/resources/overrides routes). Items 4 (`ConflictProjection`), 6, 7 and 8 still stand in part. See 'What remains' in section 1 for the live list.

1. **The write path is not reachable from HTTP.** `Container` (`app/container.py`) holds only the readiness service and the engine. There is no `SystemClock`, no `UuidIdSource` (`app/clients/` is empty), no session factory, no `ScheduleWriteService`, no `Policy` built from `campus_gap_minutes`. Tests construct everything by hand.
2. **No authentication.** No login, no session token issue/verify, no `get_actor`. PyJWT is installed and unused. The security schemes in the OpenAPI are declarations only.
3. **All business routes are 501 stubs** (section 11.1).
4. **No `ConflictProjection` (AD-23).** The example payloads contain a hand-written `with_event`; real responses need the projection (other club's non-DRAFT event, minimal fields only).
5. **Compose smoke automation is still missing.** The synthetic data seed and demo personas now exist, but a scripted `/ready` → login → chat → confirm compose check is not yet committed.
6. **Error mapping from service errors to the envelope does not exist** (section 17.5 gives the table). `ErrorCode` lacks codes for a duplicate override and for missing evidence (recommended additions in 17.1).
7. **Agent is a skeleton.** No HTTP clients, orchestration, tools, provider or Core `agent/chat` route; no `agent_actions` table, so the facade cannot persist proposals.
8. **Other tables missing:** commitments, tasks, dependencies, change proposals, report drafts, publications, registrations, student-private tables. Plans 01 (later steps), 05 and 06 need them.
9. **Two hosted-page links to an AI tool's site are still committed** in `ARCHITECTURE-SPINE.md` (frontmatter `companions:`) and `.memlog.md` (one entry), pointing at a private hosted walkthrough page. The user asked only for the commit *messages* to be cleaned, so they were left. **Ask before removing** (recommended: remove, in a normal commit).
10. **`walkthrough.html`** (in the spine directory) still lists six decisions as open questions for the team. They were later confirmed by the owner. It is a team-alignment page; leave it unless asked.
11. **Cross-doc contradictions not yet fixed** (the spine says to fix each in the change that implements the affected slice): `AGENTS.md` line ~590 says "BM25/full-text" while `PLAN.md`, `CONTEXT_ARCHITECTURE.md` and Plan 02 say SPLADE; Plan 05 batch 1 names `migrations/0002_student_registration.sql` (Core uses Alembic `NNNN_slug.py`, and `0002` is taken); `contracts/CONTRACTS.md` lacks `constraint`/`evaluated_as`/`as_status`, `AgentAction` types and confirm, `ConflictProjection`, `StudentEventView` and the error codes; `PLAN.md` section 8 lacks the new routes; the RAG plan lives outside `Implementation_Plans/` and has no error envelope; `prompts/feature-implementation-prompt.md` line 28 says "Do not commit" which conflicts with `AGENTS.md`.
12. **RAG contract unverified** (4.3). The Agent mirror is a reading of a plan. Also the RAG owner has not adopted `X-Request-ID` or the error envelope (AD-19 asked them to).
13. **Groq structured output** (`json_schema` strict mode) for `llama-3.3-70b-versatile` is unconfirmed; AD-11 relies on tool use plus Pydantic validation. Confirm when the provider lands.
14. **No CI.** `make verify` is the contract; nothing runs it automatically. Wiring GitHub Actions was deferred.
15. **Single database role.** Compose uses one superuser; AD-20 wants a role per service with schema grants. Not implemented.
16. **`0002` was amended in place** (section 10). Do not repeat it once anyone has applied it.
17. **Unpushed work:** 23 commits plus this file. `origin/backend-ai` is behind. If the machine is lost, that work is lost.
18. **`docs/presentations/Campus-Cue.pdf`** untracked; leave it.
19. **Examples' venue name:** example messages come from the engine and do not mention venue names (a projection concern).
20. **`GET /events` visibility is undecided** (PLAN open decision 8, section 16).

---

## 16. Decisions still open

From `PLAN.md` section 16, with the status as of today:

| # | Decision | Status / what the code assumes |
|---|---|---|
| 1 | Is the 2-hour gap a verified campus policy? | Treated as an **unverified planning rule**, configurable (`CAMPUS_GAP_MINUTES`), labeled in messages |
| 2 | Which states block vs warn? | Decided in AD-5: only CONFIRMED vs CONFIRMED blocks; everything else warns |
| 3 | Roles and who may confirm | Decided for now: only CAMPUS_ADMIN confirms/overrides; widening is a change to the `authz` rule table only |
| 4 | Web framework and Core language | Core = Python/FastAPI; web = Next.js (teammate) |
| 5 | Embedding model / SPLADE checkpoint | RAG owner |
| 6 | Allowed sources and access classes | `SOURCE_REGISTRY.md`; Agent currently has one access level `CAMPUS_PUBLIC` |
| 7 | Report formats / resource verification workflow | open; Plan 06 and the reports slice |
| 8 | Tentative cross-club visibility | AD-23 assumption: DRAFT is private; PROPOSED-or-later events share a minimal field set. **Needs a decision for `GET /events`**: recommended: list own-club events in full, other clubs' non-DRAFT events as a minimal summary (needs a summary DTO), campus admin sees all in full |
| 9 | Student publication audience, registration fields | open; Plan 05 |
| 10 | Attendance-warning language/threshold | warnings stay advisory |

Also open from the spine: `Deferred` items (real SSO, official gap validity, persisted chat history, same-venue GiST exclusion constraint as a backstop, notifications, CI wiring).

---

## 17. The next milestone, designed in detail (P12 to P15)

> **Superseded in part (2026-10-11):** P12 to P14 are built (by a second agent, plus Mrudula's routes). P15 (seeds, end-to-end) is not. The Core-side Agent integration, which this section does not cover, is now the critical path; section 18 item 2 sketches it.

This is a **recommendation**, consistent with the spine and the existing code. Per section 2.7, take it unless the user redirects. Write the batch plan into `Implementation_Plans/01` first (AGENTS.md section 14), with 2 to 3 files per batch.

### 17.1 P12: contract additions (one atomic Core + Agent + examples commit)
Add to Core's OpenAPI (all additive; remember the Agent mirror must follow where shared names change):

1. **`POST /api/v1/auth/demo-login`** body `DemoLoginRequest {email}` (`extra="forbid"`) -> `SessionOut {access_token, token_type: "bearer", expires_at, user: UserOut}`. Always registered; outside `APP_ENV` in {local, test, demo} it returns `404 NOT_FOUND`. Plus **`GET /api/v1/me`** -> `UserOut {id, email, display_name, campus_admin, memberships[{club_id, club_name, role}], synthetic}`.
2. **`POST /api/v1/events/{event_id}/transitions`** body `EventTransitionRequest {target, expected_revision >= 1, evidence?: EvidenceIn}` + `Idempotency-Key` header -> `EventTransitionOut {event: EventOut, conflicts: [Conflict]}`. `target` is a subset enum (`PROPOSED|SUBMITTED|CONFIRMED|REJECTED|CANCELLED|COMPLETED`; never DRAFT). `EvidenceIn {kind (1..40), reference (1..2000), issuer?, captured_at}`.
3. **`POST /api/v1/overrides`** body `OverrideCreate {scope, event_a_id, event_b_id, reason (1..2000), evidence?}` (`extra="forbid"`; **no `authorized_by` field exists**) -> `201 OverrideOut {id, scope, event_a_id, event_b_id, reason, authorized_by, evidence_id, created_at}`.
4. **`ErrorCode` additions (additive):** `DUPLICATE_OVERRIDE` (409) and `EVIDENCE_REQUIRED` (422). Add to `STATUS_BY_CODE`, to Core `domain/enums.py`, **and to the Agent's `schemas/enums.py`**; the Agent's enum-equality test will fail until you do.
5. Update the stub/real markers: routes you implement drop `x-implementation-status: stub` and the 501 response.
6. Examples for each new request/response; add to `EXAMPLES` in `test_examples.py`. Update `contracts/CONTRACTS.md` and `PLAN.md` section 8 (item 11 in section 15).

### 17.2 P13: demo-login and session tokens (AD-21, AD-22)
- Session token: **HS256 via PyJWT**, claims `iss=core`, `sub=<user id>`, `iat`, `exp` (suggest 8 hours for the demo), `jti`. Sign with `SESSION_SIGNING_KEY`. Verify with an explicit `algorithms=["HS256"]` list (reject `alg=none` and algorithm confusion), check `iss`, `exp`; **ignore every claim except `sub`**. Delegation tokens (`aud=agent-tools`, <= 120 s, signed with the *different* `DELEGATION_SIGNING_KEY`) are rejected on every `/api/v1` route and accepted only on `/internal/v1`.
- `get_actor` dependency: verify token -> `SqlActorReader.load_actor(sub)` (roles from the database on **every request**) -> `Actor`. Unknown user -> 401 `UNAUTHENTICATED`.
- Put token logic behind a service port (`TokenService`: `issue(user_id)`, `verify(token)`), with the PyJWT adapter in `app/clients/` and a fake for tests. `api/` cannot import `jwt` (import-linter forbids it in `services/`; the adapter in `clients/` may).
- Internal routes: constant-time compare of `X-Internal-Key` (`hmac.compare_digest`) when `APP_ENV != local`.
- Tests: tampered signature, expired, wrong `iss`, wrong algorithm, delegation token on a public route, session token on an internal route, deleted user, role change takes effect on the next request, demo-login refused when `APP_ENV` is not allowed.

### 17.3 P14: wiring and real routes
**Composition root** (`app/container.py`, `app/main.py`): add `app/clients/system.py` with `SystemClock` (`datetime.now(UTC)`) and `UuidIdSource` (`uuid4()`) (ambient state is allowed in `clients/`). Build `sessionmaker(engine, expire_on_commit=False)`, `ScheduleWriteService(lambda: SqlUnitOfWork(factory), clock=..., ids=..., policy=Policy(timedelta(minutes=settings.campus_gap_minutes)))`, the token service, and read services. Put them on `app.state`; `api/deps.py` reads them with `cast`, exactly like `get_readiness`.

**Layering you must respect:** routes may import `services`, `schemas`, `domain` only. So the read side needs *services* too:
- `EventQueryService` (or similar) over the plain `UnitOfWork`: `get`, `list` (filters `club_id`, `status`, `resource_id`, `starts_after`, `starts_before`, `limit` <= 200, `offset`), authorizing `VIEW_EVENT` and returning FULL vs SUMMARY per `Decision.visibility`.
- `ConflictCheckService`: same loading and `evaluate` as `commit` but **no lock and no writes**, `advisory=True`, `as_status` and the `model_fields_set` rule for `resource_id` (omitted = keep stored; explicit `null` = no venue), unsaved candidate for the facade.
- `ResourceQueryService`: list/get with `kind`, `q`, pagination.
- New port methods will be needed (`EventReader.list(...)`, `ResourceReader.list/get`, `ClubReader.names`, `ResourceReader.names`), with SQL adapters, fake implementations in `tests/fakes.py`, and tests. Do not break the existing protocol-property convention.
- `ConflictProjection` (in `services/`): domain `Conflict` -> a projected conflict with `with_event` (title, club id and name, window, venue id and name, status, audience tags) for another club's non-DRAFT event; full detail for the requester's own club; the single place conflicts are shaped for any caller, including the Agent facade.
- `api/mappers.py`: pure functions turning service records into `EventOut`/`ResourceOut`/`Conflict` wire models (times -> IST through `CampusDatetime`). Wire schemas cannot import services, so mapping lives in `api/`.

### 17.4 Route behavior
- `POST /events`: build `RequestContext(actor, request_id=request.state.request_id, idempotency_key=Idempotency-Key header)`, call `create_event`, return `201` with `EventCreatedOut`. A replay must return the **same status** (the stored `status_code`); the service returns `replayed=True`.
- `POST /events/{id}/transitions`: call `transition_event`; `200`.
- `POST /overrides`: `create_override`; `201`.
- `POST /events/{id}/conflict-check`: `ConflictCheckService`; body optional.
- Reads: `GET /events`, `GET /events/{id}`, `GET /resources`, `GET /resources/{id}`.
- Every route is a sync `def` (AD-3). Never `commit()` in a handler (handlers never commit; the service owns the unit of work).

### 17.5 Error mapping (service/domain error -> envelope)
| Raised | HTTP | `code` | `details` |
|---|---|---|---|
| `NotAuthorizedError` | 403 | `FORBIDDEN` | `[{"reason": decision.reason}]` (reason enum only) |
| `NotFoundError` | 404 | `NOT_FOUND` | |
| `ConflictDetectedError` | 409 | `CONFLICT_DETECTED` | the **projected** conflicts (never raw engine output) |
| `StaleRevisionError` | 409 | `STALE_REVISION` | `[{"expected": n, "actual": m}]` |
| `InvalidTransitionError` | 409 | `INVALID_TRANSITION` | `[{"from": ..., "to": ...}]` |
| `IdempotencyMismatchError` | 422 | `IDEMPOTENCY_MISMATCH` | |
| `EvidenceRequiredError` | 422 | `EVIDENCE_REQUIRED` (new) | |
| `InvalidRequestError`, `ValueError` from `NewEvent` | 422 | `VALIDATION_ERROR` | |
| `DuplicateOverrideError` | 409 | `DUPLICATE_OVERRIDE` (new) | |
Register one handler per class in `install_error_handlers`, or translate in a thin `api/` helper. Test each mapping through the real route.

### 17.6 P15: seeds and end-to-end
- `app/seed.py` (or `scripts/seed.py`) that **refuses** to run unless `APP_ENV` is in {local, test, demo}, idempotent, every row `is_synthetic=true`: one campus admin, two clubs each with an organizer and a club admin, a handful of venues and services (names invented, clearly synthetic), and a few events in different statuses including a CONFIRMED one. Demo-login personas map to these users.
- End-to-end tests (TestClient + PostgreSQL) for the `AGENTS.md` 10.1 list: (1) create a tentative proposal; (2) tentative overlap against unconfirmed proposals returns warnings; (3) same-venue overlap against a confirmed event blocks the confirmation; (4) cross-venue gap < 120 minutes blocks; (5) an authorized campus-gap override still rejects a venue overlap; (6) a venue change marks commitments for revalidation (needs commitments, so defer or stub); (7) policy answer with a citation (RAG, later); (8) report draft flags missing facts (later). Items 1 to 5 are achievable in this milestone.
- Compose smoke test: `docker compose up --build core-api agent-api`, `POST /api/v1/auth/demo-login`, create -> propose -> submit -> confirm a few events by `curl`, observe the 409.

### 17.7 Definition of done for the milestone
`make verify` exit 0 in both services; contracts regenerated with no drift; the stubs listed in 17.1 to 17.4 are real or explicitly still stubs; plan execution record updated (with deviations and evidence); `contracts/CONTRACTS.md` and `PLAN.md` section 8 updated; per-commit isolation check clean; no AI mentions in any commit message; the user told what was assumed.

---

## 18. After the HTTP milestone

In rough order, each needs its own plan batches.

1. **Plan 03, the Agent (the other half of this workstream).** Real HTTP clients (`HttpCoreClient`, `HttpRagClient`) with `respx` tests against the contract examples, typed errors from status/envelope, `X-Request-ID` and `X-Internal-Key` forwarding, the delegation token passed through unmodified and never logged. Then the orchestration loop (code-owned; max 6 tool calls, 20 s deadline, 5 s per tool, 16 KB tool output with `truncated`), a static tool registry with Pydantic input/output models and an `effect` of `READ` or `PROPOSE`, the **fake LLM provider** first (deterministic, no network), then the Groq provider (SDK 1.7.0, tool use plus validation). Missing critical fields (date, start, end, venue) produce a clarifying question, never a default. Untrusted-data delimiting; citations assembled from RAG metadata by code; policy claims without a valid evidence reference removed. Prompt-injection tests with malicious user text and retrieved passages.
2. **Core side of the Agent:** `POST /api/v1/agent/chat` mints the delegation JWT (HS256, `aud=agent-tools`, <= 120 s, only for organizer-class users) and calls the Agent with `httpx.Client` (timeout above the turn deadline); the `agent_actions` table (+ migration `0003`), `POST /internal/v1/agent-actions` (dry-runs the operation, stores conflicts with the proposal), the facade read tools, and `POST /api/v1/agent-actions/{id}/confirm|reject` (confirm is idempotent per action id, re-validates inside the lock via the same write path, and sets `reported_by` to the confirming human).
3. **Change impact (AD-14):** `event_dependencies`, `change_proposals`, `domain/impact`, the two-phase apply through `commit` with `demote_on_schedule_change` and `mark_needs_revalidation`; dependency-bearing fields editable only through apply.
4. **Commitments and evidence endpoints** (tables, routes, `VerifiedFacts`).
5. **Reports (AD-15)**, **student feed and private registration risk (AD-13, Plan 05, schema `student_private`)**, **official source ingestion (Plan 06, allow-listed fetch adapter)**.
6. **Hardening:** per-service database roles, CI, optional same-venue GiST exclusion constraint as a backstop, rate limiting, metrics.

---

## 19. Traps and lessons learned

- **Zone-aware arithmetic is wall-clock arithmetic.** Always normalize to UTC before adding a `timedelta`. The engine does so in `Interval`; keep it that way.
- **`ruff format` changes text under you.** Re-read before scripted edits.
- **SQLAlchemy:** a Core `UPDATE` leaves ORM copies stale (the adapter uses `populate_existing` and `expire_all`). `Session.execute(update(...))` needs a `cast` to `CursorResult` for `.rowcount`. `Mapped[UUID]` is native `uuid`. `ARRAY`/`JSONB` are PostgreSQL-only (fine; adapters may be PG-specific).
- **Protocols:** use read-only properties for members so adapters may expose more specific types.
- **Pydantic `extra="forbid"`** on every request model is a security feature (it is what stops `status` and `authorized_by` from being accepted); a test asserts the contract contains neither `authorized_by` nor `ignore_conflicts`.
- **Idempotency is checked inside the lock**, after authorization, and a refused request never stores its key.
- **Do not let a handler catch exceptions around `commit`**; let service errors propagate to the registered handlers.
- **structlog is global.** `configure_logging` called in a test leaks; the autouse reset fixture exists for that reason.
- **Starlette `TestClient`** wants `raise_server_exceptions=False` to see the 500 envelope.
- **Compose:** never publish Postgres on 5432 (taken). Do not run `docker compose down -v` against anything you did not start.
- **import-linter** needs every module named in a contract to exist; when you add a module to a contract, create it first. The guard test copies the real `.importlinter` into a throwaway tree, so add the new module names to `_make_tree` too.
- **`alembic check`** ignores CHECK constraints and triggers; the constraint tests are what cover them.
- **A passing run proves little until you have seen it fail.** The race test's control run is the model to copy.
- **Don't trust remembered state.** Re-run the first-ten-minutes commands (section 3).

---

## 20. Performance and measurements

Measured on this machine (single run, not a benchmark): Core unit and contract suite ~8 s (494 tests); Core integration suite ~11 s (96 tests, one shared PostgreSQL container); the race file ~6.6 s (the lock-enabled run deliberately waits 1.5 s at the rendezvous); Agent suite ~3 s (176 tests); `make verify` Core ~25 s fast / ~45 s full. Container build for Core, cached, a few seconds. No latency, throughput or memory measurements of the services exist. The conflict query is bounded to a time window (O(events near the candidate)), and `ix_events_end_at` supports it; nothing has been load-tested.

---

## 21. Suggested starting point

1. Run the commands in section 3. If anything is red, fix that before anything else, and tell the user.
2. `git fetch`; check whether the teammate pushed. If `main` moved, merge `main` into `backend-ai` and re-verify before building.
3. Ask (or apply 2.7): push `backend-ai` now? Recommended yes, a fast-forward, after the attribution check in 2.1.
4. Write the P12 to P15 batches into `Implementation_Plans/01` using section 17 as the source.
5. Start with **P12** (contract-first atomic commit), then **P13**, then wire the container (P14), then seeds and end-to-end (P15). Commit each 2 to 3 file slice behind the gate, with no attribution lines.
6. Update this file (and the plan execution record) before you stop.

---

## Appendix A: commit ledger

All commits on `backend-ai` since the old `main` tip `a33b7e6` (82). Hashes are current. `*` marks commits that are **local only** (not on `origin/backend-ai`). Two are merge commits (`095d16b` the branch's merge of main; `d3be84f` the GitHub PR merge).

```
01  `9d7192b` docs(core): add backend and agent architecture spine
02  `0648c50` docs(core): finalize spine and record plan 00 execution
03  `98dbfe7` chore(infra): ignore env files and add example settings
04  `ddf51db` chore(core): scaffold core-api project and tooling
05  `5c7bbf1` feat(core): add domain enums and clock primitives
06  `488f6bd` feat(core): add typed settings
07  `47d5f0d` feat(core): add json logging and request id middleware
08  `d94a80b` feat(core): add error envelope and exception handlers
09  `7a74dd7` feat(core): add readiness evaluation with a fake probe
10  `4216ace` feat(core): add baseline migration and models base
11  `4297282` chore(core): add alembic config and migration chain test
12  `107cd21` feat(core): add sql readiness probe
13  `b9ca916` test(core): verify migrations on postgres 18
14  `d16a9e5` feat(core): add health and ready routes
15  `e8c5864` feat(core): define event, resource and agent wire schemas
16  `282bb70` test(core): cover wire schema rules
17  `e880c54` feat(core): add typed event and resource route stubs
18  `54871c6` feat(core): add typed agent and facade route stubs
19  `292b5b3` feat(core): add app factory and container
20  `34f6888` test(core): cover stub routes and the openapi contract
21  `7936fca` chore(core): enforce hexagonal layering and ban ambient time
22  `6897e27` test(core): prove layering and ruff guards fire
23  `63631d2` feat(contracts): export core openapi and shared schemas
24  `d784c84` test(contracts): fail on core contract drift
25  `9125c81` docs(contracts): add error and citation examples
26  `c97e5ba` docs(contracts): add venue overlap and campus gap examples
27  `6804705` docs(contracts): add tentative overlap and unknown availability examples
28  `dc2e5a5` docs(contracts): add agent action and chat examples
29  `e0ff7e0` docs(contracts): add event and conflict check examples
30  `e80cac8` test(contracts): validate examples against schemas
31  `2c1ec82` chore(core): add container image
32  `255ce48` chore(agent): scaffold agent-api project and tooling
33  `66baa95` feat(agent): add wire enums, common types and text constraints
34  `27fdebd` feat(agent): add json logging and request id middleware
35  `ffd1361` feat(agent): add error envelope and exception handlers
36  `4b3797a` feat(agent): add typed settings
37  `440daec` feat(agent): define core, chat and rag wire schemas
38  `f8e4f5a` test(agent): cover wire schema rules
39  `9841533` feat(agent): add clock, core port and typed port errors
40  `df57995` feat(agent): add rag port and deterministic fakes
41  `3fe75f8` feat(agent): add readiness evaluation
42  `6667364` feat(agent): add health route and typed agent stubs
43  `6a98084` feat(agent): add app factory and container
44  `f574a9d` test(agent): cover stub routes
45  `7b75477` chore(agent): enforce port and adapter layering
46  `10938ce` chore(agent): ban ambient time in deterministic layers
47  `8d95a15` test(agent): prove layering and ruff guards fire
48  `53c5705` feat(contracts): export agent openapi and check it against core
49  `d3e0f8e` chore(agent): add container image
50  `de307b7` chore(infra): add compose for postgres, core and agent
51  `9e078cc` docs(core): plan the conflict engine slice
52  `0ecfde3` feat(core): add half-open interval and campus gap primitives
53  `2e70003` feat(core): add the deterministic conflict engine
54  `8486435` test(core): add property tests for the conflict engine
55  `bbaf957` feat(contracts): preview confirmation with as_status and align examples
56  `c06bbf6` docs(core): plan authorization and lifecycle batches
57  `40b1354` feat(core): add the single authorization decision point
58  `724cab0` feat(core): add event and commitment lifecycle transitions
59  `095d16b` chore: merge main into backend-ai
60* `d3be84f` Merge pull request #2 from Mrudula-itsjuzme/backend-ai
61* `75ec898` docs(core): plan the persistence and write path slice
62* `fc9eb82` test(core): derive the expected migration head from the code
63* `4e3b92d` fix(core): compare only schema core when checking migrations
64* `d477732` feat(core): add the persistence schema for events and their history
65* `913e2fa` test(core): prove the schema rejects invalid rows
66* `40f7d04` feat(core): define the write path ports and errors
67* `782890d` feat(core): serialise events, conflicts and overrides to plain json
68* `2f0a057` feat(core): expose the action a status change requires
69* `38bbc6f` feat(core): let the write path check that clubs and venues exist
70* `f9f1074` test(core): reset logging configuration between tests
71* `709c14d` refactor(core): expose port members as read-only properties
72* `5966cac` feat(core): add the single schedule write path
73* `c42fef9` chore(core): allow only the write service to import the event writers
74* `3f01c34` feat(core): load only the events near the candidate when checking conflicts
75* `70c7247` test(core): prove the nearby-events window never changes the engine result
76* `8aa0281` feat(core): index events by end time for the conflict window query
77* `f6d0b67` refactor(core): share the sql seeding helpers between integration tests
78* `fdd38e2` feat(core): add the postgres adapters for events, overrides and the campus lock
79* `164e936` feat(core): add the sql unit of work with audit, evidence and idempotency stores
80* `12f123f` test(core): verify the write path scenarios on postgres 18
81* `ee65480` test(core): prove the campus lock under racing sessions on postgres 18
82* `a266f18` docs(core): record the persistence and write path slice
```

---

## Appendix B: file map with sizes

Tracked files with line counts (generated from git on the day of writing).

```
    33  .env.example
    31  .gitignore
   136  Implementation_Plans/00-foundation-and-contracts.md
   227  Implementation_Plans/01-core-scheduling-and-events.md
    77  Implementation_Plans/02-rag-hybrid-retrieval.md
    84  Implementation_Plans/03-agent-tools-and-orchestration.md
    38  Implementation_Plans/04-frontend-vertical-slice.md
    87  Implementation_Plans/05-student-registration-risk.md
    76  Implementation_Plans/06-official-source-ingestion.md
   146  contracts/CONTRACTS.md
   725  contracts/agent-api.openapi.yaml
  1855  contracts/core-api.openapi.yaml
    37  contracts/examples/agent-action.proposed.json
     9  contracts/examples/agent-chat.request.json
    79  contracts/examples/agent-chat.response.json
    10  contracts/examples/citation.json
    63  contracts/examples/conflict-check.response.json
    27  contracts/examples/conflict.campus-gap-violation.json
    27  contracts/examples/conflict.tentative-overlap.json
    13  contracts/examples/conflict.unknown-availability.json
    27  contracts/examples/conflict.venue-overlap.json
    61  contracts/examples/error-envelope.conflict-detected.json
     6  contracts/examples/error-envelope.not-implemented.json
    12  contracts/examples/event-create.request.json
    36  contracts/examples/event-created.response.json
   405  contracts/schemas/shared.schema.json
    92  docker-compose.yml
    64  docs/architecture/architecture-campuscue-backend-ai-2026-10-10/.memlog.md
   392  docs/architecture/architecture-campuscue-backend-ai-2026-10-10/ARCHITECTURE-SPINE.md
    12  services/agent-api/.dockerignore
   120  services/agent-api/.importlinter
    29  services/agent-api/Dockerfile
    30  services/agent-api/Makefile
     1  services/agent-api/app/__init__.py
     0  services/agent-api/app/api/__init__.py
    32  services/agent-api/app/api/deps.py
   157  services/agent-api/app/api/errors.py
    63  services/agent-api/app/api/middleware.py
     0  services/agent-api/app/api/routes/__init__.py
    53  services/agent-api/app/api/routes/agent.py
    38  services/agent-api/app/api/routes/health.py
     0  services/agent-api/app/clients/__init__.py
   169  services/agent-api/app/clients/fakes.py
    22  services/agent-api/app/container.py
    51  services/agent-api/app/logging.py
    47  services/agent-api/app/main.py
     0  services/agent-api/app/orchestration/__init__.py
    28  services/agent-api/app/orchestration/readiness.py
     1  services/agent-api/app/orchestration/ruff.toml
     0  services/agent-api/app/ports/__init__.py
    18  services/agent-api/app/ports/clock.py
    35  services/agent-api/app/ports/core.py
    35  services/agent-api/app/ports/errors.py
    11  services/agent-api/app/ports/rag.py
     1  services/agent-api/app/ports/ruff.toml
     0  services/agent-api/app/providers/__init__.py
     0  services/agent-api/app/schemas/__init__.py
    75  services/agent-api/app/schemas/chat.py
    32  services/agent-api/app/schemas/common.py
   127  services/agent-api/app/schemas/core.py
    90  services/agent-api/app/schemas/enums.py
    20  services/agent-api/app/schemas/health.py
    52  services/agent-api/app/schemas/rag.py
     8  services/agent-api/app/schemas/text.py
    65  services/agent-api/app/settings.py
     0  services/agent-api/app/tools/__init__.py
     1  services/agent-api/app/tools/ruff.toml
    55  services/agent-api/pyproject.toml
    14  services/agent-api/ruff.strict.toml
    12  services/agent-api/ruff.toml
     0  services/agent-api/scripts/__init__.py
    69  services/agent-api/scripts/export_contracts.py
     0  services/agent-api/tests/__init__.py
     0  services/agent-api/tests/contract/__init__.py
   278  services/agent-api/tests/contract/test_contract.py
     0  services/agent-api/tests/unit/__init__.py
   120  services/agent-api/tests/unit/test_architecture_guards.py
   145  services/agent-api/tests/unit/test_errors.py
   235  services/agent-api/tests/unit/test_fakes.py
    82  services/agent-api/tests/unit/test_health_routes.py
   106  services/agent-api/tests/unit/test_request_id.py
    69  services/agent-api/tests/unit/test_schemas.py
    76  services/agent-api/tests/unit/test_settings.py
    98  services/agent-api/tests/unit/test_stub_routes.py
    13  services/core-api/.dockerignore
   129  services/core-api/.importlinter
    31  services/core-api/Dockerfile
    36  services/core-api/Makefile
     7  services/core-api/alembic.ini
     1  services/core-api/app/__init__.py
     0  services/core-api/app/api/__init__.py
    33  services/core-api/app/api/deps.py
   157  services/core-api/app/api/errors.py
    63  services/core-api/app/api/middleware.py
     0  services/core-api/app/api/routes/__init__.py
    87  services/core-api/app/api/routes/agent.py
    91  services/core-api/app/api/routes/events.py
    39  services/core-api/app/api/routes/health.py
    67  services/core-api/app/api/routes/internal.py
    43  services/core-api/app/api/routes/resources.py
     0  services/core-api/app/clients/__init__.py
    44  services/core-api/app/container.py
     0  services/core-api/app/domain/__init__.py
   174  services/core-api/app/domain/authz.py
   133  services/core-api/app/domain/enums.py
    62  services/core-api/app/domain/intervals.py
   214  services/core-api/app/domain/lifecycle.py
    11  services/core-api/app/domain/ruff.toml
   220  services/core-api/app/domain/scheduling.py
    47  services/core-api/app/domain/time.py
     0  services/core-api/app/ingestion/__init__.py
    51  services/core-api/app/logging.py
    47  services/core-api/app/main.py
     5  services/core-api/app/models/__init__.py
    25  services/core-api/app/models/base.py
    92  services/core-api/app/models/directory.py
   167  services/core-api/app/models/scheduling.py
     0  services/core-api/app/repositories/__init__.py
    56  services/core-api/app/repositories/directory.py
    32  services/core-api/app/repositories/health.py
    85  services/core-api/app/repositories/history.py
   217  services/core-api/app/repositories/scheduling.py
    68  services/core-api/app/repositories/unit_of_work.py
     0  services/core-api/app/schemas/__init__.py
   125  services/core-api/app/schemas/agent.py
    32  services/core-api/app/schemas/common.py
   164  services/core-api/app/schemas/events.py
    22  services/core-api/app/schemas/health.py
    33  services/core-api/app/schemas/resources.py
     0  services/core-api/app/services/__init__.py
   160  services/core-api/app/services/codec.py
    48  services/core-api/app/services/errors.py
   201  services/core-api/app/services/ports.py
    42  services/core-api/app/services/readiness.py
    12  services/core-api/app/services/ruff.toml
    71  services/core-api/app/services/schedule_store.py
   593  services/core-api/app/services/schedule_write.py
    80  services/core-api/app/settings.py
    85  services/core-api/migrations/env.py
    25  services/core-api/migrations/script.py.mako
    27  services/core-api/migrations/versions/0001_create_schemas.py
   274  services/core-api/migrations/versions/0002_core_persistence.py
    58  services/core-api/pyproject.toml
    13  services/core-api/ruff.toml
     0  services/core-api/scripts/__init__.py
   141  services/core-api/scripts/export_contracts.py
     0  services/core-api/tests/__init__.py
    67  services/core-api/tests/conftest.py
     0  services/core-api/tests/contract/__init__.py
    77  services/core-api/tests/contract/test_contracts.py
   287  services/core-api/tests/contract/test_examples.py
   314  services/core-api/tests/fakes.py
     0  services/core-api/tests/integration/__init__.py
    10  services/core-api/tests/integration/conftest.py
    94  services/core-api/tests/integration/support.py
    40  services/core-api/tests/integration/test_health_probe.py
    77  services/core-api/tests/integration/test_migrations.py
   267  services/core-api/tests/integration/test_schedule_concurrency.py
   242  services/core-api/tests/integration/test_schedule_write_sql.py
   412  services/core-api/tests/integration/test_schema_constraints.py
   326  services/core-api/tests/integration/test_sql_adapters.py
   239  services/core-api/tests/integration/test_sql_unit_of_work.py
   183  services/core-api/tests/integration/world.py
     0  services/core-api/tests/unit/__init__.py
   121  services/core-api/tests/unit/test_architecture_guards.py
   310  services/core-api/tests/unit/test_authz.py
   180  services/core-api/tests/unit/test_codec.py
   133  services/core-api/tests/unit/test_domain_primitives.py
   145  services/core-api/tests/unit/test_errors.py
    81  services/core-api/tests/unit/test_health_routes.py
   130  services/core-api/tests/unit/test_intervals.py
   361  services/core-api/tests/unit/test_lifecycle.py
    38  services/core-api/tests/unit/test_migration_chain.py
    41  services/core-api/tests/unit/test_readiness.py
   106  services/core-api/tests/unit/test_request_id.py
   806  services/core-api/tests/unit/test_schedule_write.py
   466  services/core-api/tests/unit/test_scheduling.py
   319  services/core-api/tests/unit/test_scheduling_properties.py
   232  services/core-api/tests/unit/test_schemas.py
    91  services/core-api/tests/unit/test_settings.py
   175  services/core-api/tests/unit/test_stub_routes.py
```

---

## Appendix C: helper scripts to recreate

The previous session kept these in a throwaway scratch directory (they are not in the repo and must not be committed). Recreate what you need.

### C.1 A commit helper that refuses to commit on a red gate
```bash
#!/usr/bin/env bash
# usage (from the repo root):  GATE_DIR=$PWD/services/core-api GATE_TARGET=verify ./commit.sh "subject" "Refs text" path...
set -euo pipefail
subj="$1"; ref="$2"; shift 2
if printf '%s\n%s\n' "$subj" "$ref" | grep -qiE '(cl|anthr)(aude|opic)|co-?authored|generated with'; then echo "refusing: attribution text in message"; exit 1; fi
if [ -n "${GATE_DIR:-}" ]; then
  if ! (cd "$GATE_DIR" && command make "${GATE_TARGET:-verify-fast}" > /tmp/gate.log 2>&1); then
    echo "GATE FAILED; not committing:"; tail -25 /tmp/gate.log; exit 1
  fi
fi
git add -- "$@"
staged=$(git diff --cached --name-only | sort | tr '\n' ' ')
want=$(printf '%s\n' "$@" | sort | tr '\n' ' ')
if [ "$staged" != "$want" ]; then echo "STAGED SET MISMATCH"; git restore --staged -- "$@"; exit 1; fi
git commit -q -m "$subj" -m "Refs: $ref in Implementation_Plans/01-core-scheduling-and-events.md"
echo "$(git rev-parse --short HEAD) $subj"
```
(`GATE_TARGET=verify` includes the Docker tests; use it whenever you touch SQL, models, migrations or adapters.)

### C.2 Per-commit isolation check (outline)
```python
# for each sha in `git rev-list --reverse <base>..HEAD`:
#   git archive <sha> | tar -x -C <tmpdir>
#   for each service dir that has a pyproject.toml in <tmpdir>:
#     run, with cwd=<tmpdir>/services/<svc> and the service's EXISTING venv binaries (.venv/bin/...):
#       ruff check . ; ruff format --check . ; mypy <app scripts tests that exist> ; lint-imports (if .importlinter exists)
#       pytest -q -x -m "not integration" -p no:cacheprovider ; python -m scripts.export_contracts --check (if the script and contracts/ exist)
#   print ok/FAIL per commit and fail on any non-zero step
```
Import-linter and mypy configs name modules that must exist, so the check also catches a commit whose config runs ahead of its code.

### C.3 Mutation-check pattern
```python
# For a module M and its tests T: for each (name, old, new) in a list of deliberate breakages,
#   assert M_text.count(old) == 1 ; write M_text.replace(old, new) ; run T ; record pass/fail ; ALWAYS restore M in `finally`
# Expect every mutant to fail some test; investigate survivors (a gap, or an equivalent mutant such as a lock key's numeric value).
```

### C.4 Regenerating the conflict examples
The 13 example files were produced by a script that (a) imported `app.domain.scheduling.evaluate` from `services/core-api`, (b) built `ScheduledEvent` scenarios (overlapping confirmed pair, non-overlapping gap violation, tentative pair, a draft at an unconfirmed venue), (c) converted each `Conflict` to wire form (IST ISO strings, `constraint`, `message`, `override_required`) and added a hand-written `with_event` summary, then (d) wrote JSON with `indent=2`. `tests/contract/test_examples.py` holds the same scenarios with the same ids and will tell you exactly which file drifted. Ids used: club `7b1c4c1e-5d0a-4f4e-9a52-3f2a1c9d0001/0002`, events `3d6f0b9a-8c1e-4b7a-a1d2-0000000000a1/b1/b2`, venue `5e0a1c33-2f7d-4d1b-8e64-0000000000c1/c2`, action `9a2b6c7d-1e3f-4a5b-8c9d-0000000000d1`.
