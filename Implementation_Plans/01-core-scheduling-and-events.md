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

## Risks
- Campus-wide gap may be a product preference rather than official policy.
- Cross-row temporal constraints require careful concurrency handling.
- The meaning of “consecutive events” needs stakeholder agreement.

## Deviation log
- Initial plan dated 2026-10-10; implementation not started.
