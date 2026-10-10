# Implementation Plan 01: Core Events and Scheduling

**Status:** Planned  
**Owner:** Core API workstream  
**Dependencies:** Plan 00 contracts; PostgreSQL available

## Objective
Implement event proposal CRUD, resource references, deterministic conflict checks, status transitions, scoped overrides, event revisions and audit history.

## Preconditions
- Confirm interval semantics and status vocabulary.
- Keep 120-minute gap configurable and label it as a CampusCue planning rule until verified.
- Agree which states generate warnings versus blocking conflicts.
- Agree authorized role for official confirmations and overrides.

## Files expected
- `services/core-api/app/domain/scheduling.py`
- `services/core-api/app/domain/events.py`
- `services/core-api/app/api/routes/events.py`
- `services/core-api/app/api/routes/resources.py`
- `services/core-api/app/models/`
- `services/core-api/app/schemas/`
- `services/core-api/app/repositories/`
- `services/core-api/app/services/`
- `services/core-api/migrations/`
- `services/core-api/tests/unit/test_scheduling.py`
- `services/core-api/tests/integration/`
- contract fixtures under `contracts/`

Exact module names may be adjusted to the selected project layout, but update this plan before broad implementation.

## Ordered steps
1. Add event/resource/commitment/evidence/revision/override/audit schema and migrations.
2. Add event create/list/get endpoints with strict input validation.
3. Implement half-open interval overlap and campus-gap functions as pure functions.
4. Add query for candidate events excluding the event being edited and excluding cancelled/rejected records per agreed policy.
5. Return separate venue, campus-gap, tentative and dependency conflict classes.
6. Add explicit `UNKNOWN_AVAILABILITY` representation when no authoritative source exists.
7. Implement status transition validation; do not let free-form client strings set confirmed state.
8. Add evidence validation and role checks for official confirmation.
9. Add scoped override model and authorization; ensure campus-gap override does not bypass venue overlap.
10. Add transactional conflict recheck at mutation/confirmation time.
11. Add same-venue exclusion constraint for confirmed bookings if compatible with chosen PostgreSQL model.
12. Add event revisions, audit events, expected-version checks and idempotency for mutations.
13. Add resource catalog endpoints with source and verification metadata.
14. Seed synthetic demo events and mark them synthetic.
15. Add unit, integration, concurrency and contract tests.

## Core interval cases
- `09:00–11:00` followed by `13:00–14:00`: gap passes exactly at 120 minutes.
- `09:00–11:00` followed by `12:59–14:00`: gap fails.
- `09:00–12:00` and `10:00–11:00`: overlap.
- Different venues with 30-minute gap: campus-gap violation under current assumption.
- Same venue overlapping confirmed events: hard venue conflict absent explicit venue override.
- Cancelled event: no active scheduling constraint under agreed lifecycle.
- Same event excluded during its own reschedule check.
- Concurrent proposals: both cannot bypass transaction-safe validation.

## API contracts
- `POST /api/v1/events`
- `GET /api/v1/events`
- `GET /api/v1/events/{event_id}`
- `POST /api/v1/events/{event_id}/conflict-check`
- `POST /api/v1/events/{event_id}/change-proposals`
- `GET /api/v1/events/{event_id}/timeline`
- `GET /api/v1/events/{event_id}/impact`
- `GET /api/v1/resources`
- `GET /api/v1/resources/{resource_id}`

## Definition of done
- All interval boundary tests pass.
- The write path rechecks relevant conflicts transactionally.
- Unauthorized confirmation/override requests fail.
- Overrides have reason, scope, actor and timestamp.
- No API reports a tentative proposal as a confirmed reservation.
- Audit history records state changes.
- Contract tests pass and OpenAPI is updated.

## Backend and AI execution: conflict engine slice (branch `backend-ai`)

**Objective:** the pure `evaluate()` function of spine AD-5 and AD-6 in `domain/`, fully tested, with no I/O, no persistence and no routes. Steps 3 to 6 and 9 of the ordered steps above, minus the database parts.

**Non-goals for this slice:** event persistence and migrations, the `pg_advisory_xact_lock` write path (AD-4), the `ConflictProjection` (AD-23), authorization (AD-21), real route handlers, and `DEPENDENCY_CONFLICT` (it needs `event_dependencies`, which does not exist yet).

**Decisions that bind the code** (spine AD-5, AD-6, AD-17, plus these slice-level calls):
- The candidate's `status` is the state being evaluated. To check a confirmation, the caller passes the candidate with `status=CONFIRMED`; both sides CONFIRMED yields `blocking`, anything else yields a `warning`.
- Overlapping same-venue events violate both constraints, and each is reported once; the constraints never short-circuit each other.
- Two events with no venue chosen never conflict on venue.
- An override matches on the unordered event pair and the constraint only, and removes both the blocking and the warning form of that constraint for that pair.
- `UNKNOWN_AVAILABILITY` is emitted for a candidate with a venue unless the venue's availability is `CONFIRMED`.
- `window`: for overlapping events, the shared interval; for non-overlapping campus-gap violations, the buffer `[earlier.end_at, earlier.end_at + gap)`.
- All arithmetic is done on UTC instants. `datetime + timedelta` on a zone-aware value is wall-clock arithmetic and is wrong across DST changes, so inputs are normalised first.
- Results are ordered blocking, warning, info, then by the other event's start time and id, then venue before gap, so output is deterministic.

### Batch P1: Interval primitives
- **Files:** `services/core-api/app/domain/intervals.py`, `services/core-api/tests/unit/test_intervals.py`
- **Verification:** `uv run pytest tests/unit/test_intervals.py`
- **Expected Commit:** `feat(core): add half-open interval and campus gap primitives`
- **Definition of Done:** exactly 120 minutes passes, 119 fails, touching intervals do not overlap, results do not depend on argument order.

### Batch P2: Conflict engine
- **Files:** `services/core-api/app/domain/scheduling.py`, `services/core-api/tests/unit/test_scheduling.py`
- **Verification:** `uv run pytest tests/unit/test_scheduling.py`
- **Expected Commit:** `feat(core): add the deterministic conflict engine`
- **Definition of Done:** every case in "Core interval cases" above has a test; a campus-gap override never removes a venue overlap.

### Batch P3: Properties
- **Files:** `services/core-api/tests/unit/test_scheduling_properties.py`
- **Verification:** `uv run pytest tests/unit/test_scheduling_properties.py`
- **Expected Commit:** `test(core): add property tests for the conflict engine`
- **Definition of Done:** symmetry, independence of the two constraints, blocking-only-when-both-confirmed and zone-independence hold for generated inputs.

### Batch P4: Contract alignment (atomic multi-service changeset)
- **Files:** Core `app/schemas/events.py`, `app/schemas/agent.py`; `contracts/core-api.openapi.yaml`, `contracts/schemas/shared.schema.json`; the 9 affected files in `contracts/examples/`; Agent `app/schemas/core.py`, `app/clients/fakes.py`; and the tests that cover them.
- **Changes:** (1) `ConflictCheckRequest.as_status` and `AgentConflictCheckRequest.as_status` let a caller preview a confirmation, because a check on a stored DRAFT can otherwise only produce warnings; (2) `ConflictCheckOut.evaluated_as` states which status was used; (3) the conflict `window` wording matches the engine; (4) example payloads are the engine's own output, and a test fails if they drift.
- **Verification:** `make verify` in both services.
- **Expected Commit:** `feat(contracts): preview confirmation with as_status and align examples with the engine`
- **Definition of Done:** both services pass `make verify`; contract drift check clean; examples equal engine output.

## Risks
- Campus-wide gap may be a product preference rather than official policy.
- Cross-row temporal constraints require careful concurrency handling.
- The meaning of “consecutive events” needs stakeholder agreement.

## Deviation log
- Initial plan dated 2026-10-10; implementation not started.
- 2026-10-10: Batch P4 exceeds 3 files by design (AGENTS.md 11.3.3, atomic multi-service changeset): the Agent's tests compare its mirror strictly against Core's contract and examples, so a required response field (`evaluated_as`) cannot land in smaller green commits. No contract is otherwise broken; `as_status` is optional.
- 2026-10-10: Added the conflict engine slice (batches P1 to P4) for the backend/AI workstream. Persistence, the write path and routes remain as the plan's later steps. Corrected the conflict `window` wording from Plan 00's schemas: for overlapping events it is the shared interval, which also fixes nested events at different venues.
