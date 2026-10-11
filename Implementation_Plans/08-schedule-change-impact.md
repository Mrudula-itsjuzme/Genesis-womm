# Implementation Plan 08: Schedule Changes and Dependency Impact

Status: In progress on `feat/schedule-change-impact` (2026-10-11).

User-selected continuation of the frontend integration. Implements architecture AD-14 using the existing campus lock, authorization table and revision/audit history.

## Contract and behavior

- Organizer/club admin may stage a change for their club; club/campus admin may apply it. Delegated Agent principals cannot stage/apply via these public APIs.
- Changes allow only `start_at`, `end_at`, `resource_id` and `expected_attendance`; omitted fields retain stored values, explicit null clears nullable fields. Invalid intervals, no-op changes and terminal events are rejected.
- Staging saves a proposal (base revision, diff, advisory conflicts/impact) without changing the event. Applying requires the current base revision and a human decision, re-evaluates under the existing campus lock, and writes event revision/audit, proposal decision and affected-item revalidation atomically.
- Interval or venue changes demote CONFIRMED to SUBMITTED and clear current verification while retaining historical evidence/revisions. Attendance-only changes do not demote the event, but revalidate matching dependencies.
- Dependency registration creates an organizer-reported task or requested commitment plus explicit field bindings. It cannot claim official acknowledgment/confirmation or resource availability. Tasks carry a revalidation flag; live commitments become NEEDS_REVALIDATION.
- Impact matches actual changed fields, groups repeated bindings per dependent item, gives deterministic reasons, and excludes closed items. Empty impact means no registered dependency matched, not that no real-world work is affected.
- List/read endpoints are scoped to the event's own club or campus admin. Retryable mutations use idempotency keys; apply replays a stored result without another write.

## Atomic implementation slices

- [ ] Pure impact function and meaningful unit tests.
- [ ] Change/operational-item persistence models, migration and model registration.
- [ ] Persistence integration tests and migration/metadata verification.
- [ ] Typed change ports and SQL adapter.
- [ ] SQL unit-of-work wiring and adapter tests.
- [ ] Authorized staging/dependency/read service and tests.
- [ ] Schedule writer apply/revalidation and transaction tests.
- [ ] Wire schemas and schema-validation tests.
- [ ] Container/dependency/app wiring with tests.
- [ ] HTTP routes, route tests and generated OpenAPI.
- [ ] Frontend generated types and typed endpoints.
- [ ] Persisted changes/impact and dependency UI with browser tests.
- [ ] Live smoke, full regression, plans and handoff.

## Verification

Run targeted red/green tests and static checks before each explicit 2–3-file commit. Final gates: Core pytest (including PostgreSQL concurrency), ruff check/format, mypy, import-linter, contract drift; web lint/type/unit/build/browser; Compose migration and live gateway smoke. Preserve pre-existing `ui_mock.png`.

## Boundaries

No outbound messages, automatic AI apply, official commitment verification UI, graph inference, resource booking claims or report/RAG changes. Dependency metadata is explicitly registered, not inferred. Existing scheduling rules and statuses remain authoritative.
