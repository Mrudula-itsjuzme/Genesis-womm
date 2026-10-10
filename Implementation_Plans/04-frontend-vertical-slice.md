# Implementation Plan 04: Frontend Vertical Slice

**Status:** Planned  
**Owner:** Frontend workstream  
**Dependencies:** Plan 00 schemas; mocked API fixtures

## Objective
Build the smallest complete interface for the primary demo: create a tentative event, inspect conflicts, ask a policy question, change venue/time, review impacts, and edit a report draft.

## Ordered steps
1. Select React/Vite or Next.js and document the choice.
2. Create API client wrappers and shared types generated from or validated against contracts.
3. Build event proposal form with explicit tentative status.
4. Build calendar/list that visually separates proposals from confirmed records.
5. Render conflict categories and explain that tentative overlap is not a booking.
6. Build resource detail view with source and verification timestamp.
7. Build policy assistant with citations that open the source/page where possible.
8. Build event commitment timeline with separate request, acknowledgment and confirmation records.
9. Build change-impact review with affected dependencies and revalidation flags.
10. Build editable report draft with missing fields highlighted.
11. Add loading, empty, timeout and dependency-unavailable states.
12. Replace mocks incrementally with Core API integration.
13. Add accessibility and responsive layout checks.

## UX invariants
- Never display “Available” unless an authorized availability source proves it.
- Show `Unknown` where availability cannot be verified.
- Never style tentative intent like a confirmed reservation.
- Explain the scope of any conflict and whether it is a warning or blocking constraint.
- Show citation title/page and preserve the original source link.
- Make generated report text editable and mark missing facts explicitly.

## Definition of done
- Primary demo is navigable without manual database edits.
- Mock mode remains available.
- Error states are visible and recoverable.
- All status labels match Core API enums.
- No frontend-only logic is treated as authoritative validation.
