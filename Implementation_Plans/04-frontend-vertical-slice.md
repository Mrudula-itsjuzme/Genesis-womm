# Implementation Plan 04: Frontend Vertical Slice

**Status:** Core-backed integration implemented; commitment/dependency extensions pending
**Owner:** Frontend workstream  
**Dependencies:** Committed Core OpenAPI; live Core gateway; synthetic browser fixtures

## Objective
Build the smallest complete interface for the primary demo: create a tentative event, inspect conflicts, ask a policy question, change venue/time, review impacts, and edit a report draft.

## Ordered steps
1. [x] Use the existing Next.js 16 / React 19 application.
2. [x] Generate wire types from Core OpenAPI and provide authenticated wrappers.
3. [x] Create tentative drafts with explicit status and idempotency.
4. [x] Load month/week/list calendars and inspect recorded event details.
5. [x] Render Core conflict categories/severity and distinguish tentative intent from bookings.
6. [x] Show venue provenance, verification/freshness and UNKNOWN availability.
7. [x] Provide multi-turn policy chat with per-reply citations, excerpts and source/page links.
8. [ ] Add commitment timeline after Core exposes request/acknowledgment/confirmation records.
9. [ ] Add persisted schedule changes and dependency revalidation after Core exposes these APIs. Current UI provides an explicitly unsaved conflict preview and authorized lifecycle transitions with evidence/revision checks.
10. [x] Build editable local reports from recorded facts and mark missing outcomes.
11. [x] Add loading, empty, retry, bounded timeout and dependency-unavailable states.
12. [x] Replace runtime mocks with Core integration; keep synthetic HTTP fixtures in tests.
13. [x] Verify keyboard dialog dismissal, mobile navigation/layout and identity/stale-response clearing.

## UX invariants
- Never display “Available” unless an authorized availability source proves it.
- Show `Unknown` where availability cannot be verified.
- Never style tentative intent like a confirmed reservation.
- Explain the scope of any conflict and whether it is a warning or blocking constraint.
- Show citation title/page and preserve the original source link.
- Make generated report text editable and mark missing facts explicitly.

## Definition of done
- Primary demo is navigable without manual database edits.
- Synthetic HTTP fixtures remain available in tests; no silent runtime mock fallback.
- Error states are visible and recoverable.
- All status labels match Core API enums.
- No frontend-only logic is treated as authoritative validation.

## Integration evidence — 2026-10-11

The detailed [integration execution record](../docs/superpowers/plans/2026-10-11-full-frontend-backend-integration.md) and [HANDOFF.md](../HANDOFF.md) contain commands and commits. Web gates pass: lint, TypeScript, 14 unit tests, production build, 11 browser regressions and one live gateway smoke test. Core regression: 1,040 passed, one empty-parameter test skipped.

Repeatable synthetic seeds support the demo without manual SQL. Reports remain local drafts; commitment timelines, dependency impact, server reports, proposal listing and real RAG ingestion/answer quality are backend-dependent.
