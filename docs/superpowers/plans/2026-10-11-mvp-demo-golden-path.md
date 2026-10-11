# CampusCue MVP Demo Golden Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a working, fully verified MVP Demo for the hackathon covering all 5 Golden Path user journeys (Calendar, Conflict Engine, Change Impact, Grounded Policy Chat, and Proposal Upload) with zero demo crashes or unhandled error screens.

**Architecture:** Connect the running Next.js frontend (`apps/web`) to Core API (`core-api:8000`) and Agent API (`agent-api:8001`) with deterministic offline fallback (`AGENT_DEMO_MODE=true`), PostgreSQL pgvector storage, and MinIO object storage.

**Tech Stack:** Next.js 15, React 19, TypeScript, Tailwind CSS, FastAPI, SQLAlchemy, PostgreSQL, MinIO, Docker Compose.

**Spec:** `PROJECT.md`, `CONTEXT_ARCHITECTURE.md`, `contracts/CONTRACTS.md`, and hackathon MVP requirements.

## Global Constraints

- **Strict MVP Scope:** Do not implement out-of-scope enterprise auth token delegation, PostgreSQL exclusion lock rewrites, or complex RAG token pruning. Focus strictly on working demo flows and user journeys.
- **Offline Reliability Invariant:** The entire demo must operate 100% offline using `AGENT_DEMO_MODE=true` and synthetic campus data (Amrita Coimbatore).
- **No Untracked Bloat:** `ui_mock.png` is in the repo root and must remain untracked. Never run `git add .` or `git add -A`.
- **Commit Cadence:** Atomic 2–3 file commits following Conventional Commits (`AGENTS.md`).

---

### Task 1: Environment & Deterministic Demo Mode Configuration

**Files:**
- Create: `.env` (derived from `.env.example` with `AGENT_DEMO_MODE=true` and `POSTGRES_PASSWORD=campuscue`)
- Modify: `docker-compose.yml:93` (ensure `AGENT_DEMO_MODE` defaults to `true` for demo resilience)
- Test: `scripts/demo_smoke.py`

**Interfaces:**
- Consumes: `.env.example`, `docker-compose.yml`
- Produces: Active environment configuration with `AGENT_DEMO_MODE=true` and valid PostgreSQL credentials.

- [ ] **Step 1: Create `.env` file**
Create `.env` in the repository root with:
```bash
POSTGRES_USER=campuscue
POSTGRES_PASSWORD=campuscue
POSTGRES_DB=campuscue
AGENT_MODEL_PROVIDER=fake
AGENT_DEMO_MODE=true
APP_ENV=local
INTERNAL_API_KEY=local-only-internal-key-not-a-secret
SESSION_SIGNING_KEY=local-only-session-key-not-a-secret-0001
DELEGATION_SIGNING_KEY=local-only-delegation-key-not-a-secret-0002
CAMPUS_GAP_MINUTES=120
CORE_API_URL=http://core-api:8000
AGENT_API_URL=http://agent-api:8001
RAG_API_URL=http://rag-api:8002
MINIO_ENDPOINT=minio:9000
MINIO_PUBLIC_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=campuscue_admin
MINIO_SECRET_KEY=campuscue_secret
```

- [ ] **Step 2: Update `docker-compose.yml` default**
Ensure `AGENT_DEMO_MODE: ${AGENT_DEMO_MODE:-true}` so containers booted without `.env` also default to demo mode.

- [ ] **Step 3: Restart containers and verify environment**
Run `docker compose up -d --force-recreate agent-api` and verify `AGENT_DEMO_MODE` is active via `curl http://localhost:8001/ready`.

- [ ] **Step 4: Commit**
`git add docker-compose.yml`
`git commit -m "chore(infra): default agent to deterministic demo mode in docker compose"`

---

### Task 2: Database Clean State & Smoke Test Verification

**Files:**
- Modify: `scripts/demo_smoke.py:182` (allow `>= 3` venues so additional catalogued campus spaces do not fail smoke test)
- Test: `scripts/demo_smoke.py`

**Interfaces:**
- Consumes: Running Core API, Agent API, and PostgreSQL database.
- Produces: 100% passing `scripts/demo_smoke.py` smoke test verification.

- [ ] **Step 1: Check smoke test assertion in `scripts/demo_smoke.py`**
In `scripts/demo_smoke.py:182`, change `check("three venues are catalogued", resources["total"] == 3)` to `resources["total"] >= 3` to support full campus venue catalogues.

- [ ] **Step 2: Run smoke test**
Run `python scripts/demo_smoke.py --verbose` and confirm all 6 sections pass:
1. The services are up (PASS)
2. Sign in (PASS)
3. The browser can talk to Core (PASS)
4. The seeded campus (PASS)
5. The assistant plans a free slot (PASS)
6. Only a person can confirm (PASS)

- [ ] **Step 3: Commit**
`git add scripts/demo_smoke.py`
`git commit -m "test(core): allow campus venue catalogue expansion in demo smoke test"`

---

### Task 3: Golden Path Screen 1 — Unified Campus Calendar (`/calendar`)

**Files:**
- Modify: `apps/web/src/components/CalendarGrid.tsx`
- Modify: `apps/web/src/app/calendar/page.tsx`
- Test: `apps/web/tests/` or browser verification

**Interfaces:**
- Consumes: `GET /api/v1/events` from `core-api:8000` via `lib/api.ts`
- Produces: Responsive monthly/weekly calendar rendering seeded events, real time intervals, and status badges (Tentative, Confirmed, Cancelled).

- [ ] **Step 1: Inspect `CalendarGrid.tsx` and `app/calendar/page.tsx`**
Ensure `CalendarGrid` fetches live events from `GET /api/v1/events` using the authenticated demo token, rendering half-open intervals `[start, end)`.

- [ ] **Step 2: Add status badge legend and tentative vs confirmed distinction**
Ensure the calendar prominently displays the product invariant: *"Tentative event proposal is not a venue booking"* and renders distinct badges for DRAFT, PROPOSED, ACKNOWLEDGED, CONFIRMED.

- [ ] **Step 3: Verify in browser**
Verify `http://localhost:3000/calendar` renders correctly without console errors.

- [ ] **Step 4: Commit**
`git add apps/web/src/components/CalendarGrid.tsx apps/web/src/app/calendar/page.tsx`
`git commit -m "feat(frontend): wire live event scheduling and status badges to calendar grid"`

---

### Task 4: Golden Path Screen 2 — Conflict Engine & Planning (`/plan`)

**Files:**
- Modify: `apps/web/src/app/plan/page.tsx`
- Modify: `apps/web/src/components/ConflictSidebar.tsx`
- Test: Live conflict check endpoint

**Interfaces:**
- Consumes: `POST /internal/v1/agent-tools/check_event_conflicts` or `POST /api/v1/events` pre-flight
- Produces: Real-time conflict feedback before event submission.

- [ ] **Step 1: Wire real-time conflict checking into `/plan`**
When selecting a venue, date, and time slot, trigger a debounced pre-flight check to `check_event_conflicts`.

- [ ] **Step 2: Update `ConflictSidebar.tsx`**
Bind `ConflictSidebar` to display actual conflict items (overlapping bookings, 120-minute gap warnings) instead of static dummy text.

- [ ] **Step 3: Verify conflict detection flow**
Select a slot that clashes with a seeded event (e.g. Synthetic Main Auditorium at overlapping hours) and verify the conflict alert appears immediately with mitigation suggestions.

- [ ] **Step 4: Commit**
`git add apps/web/src/app/plan/page.tsx apps/web/src/components/ConflictSidebar.tsx`
`git commit -m "feat(frontend): connect real-time conflict detection and dynamic conflict sidebar"`

---

### Task 5: Golden Path Screen 3 — Change Impact Assessment (`/changes`)

**Files:**
- Modify: `apps/web/src/app/changes/page.tsx`
- Modify: `apps/web/src/components/ChangeImpactList.tsx`

**Interfaces:**
- Consumes: Event change records and downstream commitments.
- Produces: Visual change impact diff highlighting affected equipment, overlapping venues, and 120-minute campus gaps.

- [ ] **Step 1: Inspect `ChangeImpactList.tsx`**
Ensure `ChangeImpactList` displays schedule shifts, equipment dependencies, and downstream notifications for organizers.

- [ ] **Step 2: Verify 120-minute gap computation**
Ensure the 120-minute campus-wide planning gap is accurately visualized with yellow warning callouts and override options.

- [ ] **Step 3: Verify in browser**
Verify `http://localhost:3000/changes` renders cleanly.

- [ ] **Step 4: Commit**
`git add apps/web/src/app/changes/page.tsx apps/web/src/components/ChangeImpactList.tsx`
`git commit -m "feat(frontend): display downstream change impact and campus gap warnings"`

---

### Task 6: Golden Path Screen 4 — Policy Assistant with Citations (`/policy`)

**Files:**
- Modify: `apps/web/src/app/policy/page.tsx`
- Modify: `apps/web/src/components/PolicyAssistant.tsx`

**Interfaces:**
- Consumes: `POST /api/v1/agent/chat`
- Produces: Interactive chat with verifiable evidence citations and proposal action buttons.

- [ ] **Step 1: Connect chat input to `POST /api/v1/agent/chat`**
Ensure messages are submitted to the agent chat endpoint with the organizer token.

- [ ] **Step 2: Render citation badges and proposed actions**
Display evidence citations (e.g. `[EVD-01] Amrita Coimbatore Event Policy §4.2`) and render action cards for `PROPOSED` event creation that require human confirmation.

- [ ] **Step 3: Test Policy Q&A in browser**
Test asking: "What are the rules for booking the Main Auditorium?" and verify the grounded response and citations appear cleanly.

- [ ] **Step 4: Commit**
`git add apps/web/src/app/policy/page.tsx apps/web/src/components/PolicyAssistant.tsx`
`git commit -m "feat(frontend): wire policy assistant chat with citations and action proposals"`

---

### Task 7: Golden Path Screen 5 — Proposal Document & MinIO Flow (`/plan` + `/reports`)

**Files:**
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/app/reports/page.tsx`

**Interfaces:**
- Consumes: `POST /api/v1/clubs/{club_id}/events/{event_id}/proposals` and MinIO presigned download URLs.
- Produces: Uploaded proposal storage and generated post-event report draft.

- [ ] **Step 1: Add proposal upload helper to `lib/api.ts`**
Add multipart upload method `uploadProposalDocument(clubId, eventId, file, token)`.

- [ ] **Step 2: Verify post-event report draft view (`/reports`)**
Ensure report view displays attendance, commitments, and editable draft summary without inventing unverified facts.

- [ ] **Step 3: Commit**
`git add apps/web/src/lib/api.ts apps/web/src/app/reports/page.tsx`
`git commit -m "feat(frontend): add proposal document upload client and post-event report draft"`

---

### Task 8: Presenter 3-Minute Walkthrough Script & Rehearsal Runbook

**Files:**
- Create: `docs/superpowers/plans/demo-script.md`

**Interfaces:**
- Consumes: All 5 Golden Path screens.
- Produces: Step-by-step speaker script for hackathon presentation.

- [ ] **Step 1: Write demo script**
Detail the exact 3-minute pitch sequence:
1. The Problem (University event planning chaos & approval friction)
2. Screen 1: Unified Calendar & Status honesty
3. Screen 2: Real-time Conflict Engine preventing double-bookings
4. Screen 3: Schedule Change Impact & 120-minute campus gap warning
5. Screen 4: Grounded Policy Assistant with attributed citations
6. Screen 5: One-click Human-in-the-Loop Confirmation & Proposal Archive

- [ ] **Step 2: Commit**
`git add docs/superpowers/plans/demo-script.md`
`git commit -m "docs: add 3-minute hackathon demo presenter script and runbook"`
