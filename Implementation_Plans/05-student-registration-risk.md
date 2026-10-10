# Implementation Plan 05: Student Discovery and Registration Risk

**Status:** Planned
**Owner:** Core API and Frontend
**Dependencies:** Plan 00 foundation and contracts, approved student authentication model, synthetic demo data

## 1. Objective and non-goals

- **Objective:** Let organizers publish events for a selected student audience. Let students discover those events, receive private exam and attendance warnings before registration, and either register internally or continue to an organizer-configured external form.
- **Non-goals:** This plan does not implement an institutional attendance API, determine attendance eligibility, scrape academic systems, expose academic data to organizers, or confirm completion of external forms.

## 2. Affected contracts and boundaries

- `contracts/CONTRACTS.md`
- `GET /api/v1/student/events`
- `POST /api/v1/events/{event_id}/registration-risk-check`
- `POST /api/v1/events/{event_id}/registrations`
- Core API owns publication, registration, risk evaluation, and authorization.
- Frontend presents only the current student's risk result. Agent and RAG do not receive academic data.

## 3. Ordered execution batches

### Batch 1: Student publication and registration persistence
- **Files:**
  - `services/core-api/app/models/student_registration.py`
  - `services/core-api/migrations/0002_student_registration.sql`
  - `services/core-api/tests/unit/test_student_registration_model.py`
- **Verification:** `pytest services/core-api/tests/unit/test_student_registration_model.py`
- **Expected commit:**
  - **Type:** `feat(core)`
  - **Message:** `feat(core): add student event publication records`
- **Definition of done:** Publication visibility and registration mode validate correctly. Internal registrations and external redirects have distinct stored states.

### Batch 2: Mock academic-risk service
- **Files:**
  - `services/core-api/app/services/academic_risk.py`
  - `services/core-api/app/api/routes/student_events.py`
  - `services/core-api/tests/unit/test_academic_risk.py`
- **Verification:** `pytest services/core-api/tests/unit/test_academic_risk.py`
- **Expected commit:**
  - **Type:** `feat(core)`
  - **Message:** `feat(core): evaluate private registration risks`
- **Definition of done:** Seeded exam, timetable, and mock attendance data produce typed advisory warnings. Missing academic data returns an explicit warning and does not block registration.

### Batch 3: Student portal client and event feed
- **Files:**
  - `apps/web/src/api/studentEvents.ts`
  - `apps/web/src/pages/StudentEventsPage.tsx`
  - `apps/web/src/pages/StudentEventsPage.test.tsx`
- **Verification:** `npm test -- StudentEventsPage.test.tsx`
- **Expected commit:**
  - **Type:** `feat(frontend)`
  - **Message:** `feat(frontend): add published student event feed`
- **Definition of done:** Students can see published events only, open details, and begin registration without organizer-only details appearing in the page.

### Batch 4: Registration decision and external redirect
- **Files:**
  - `apps/web/src/components/RegistrationRiskDialog.tsx`
  - `apps/web/src/components/RegistrationRiskDialog.test.tsx`
  - `apps/web/src/api/studentEvents.ts`
- **Verification:** `npm test -- RegistrationRiskDialog.test.tsx`
- **Expected commit:**
  - **Type:** `feat(frontend)`
  - **Message:** `feat(frontend): warn before student registration`
- **Definition of done:** The dialog presents private warnings, lets the student cancel or continue, and labels an external-form action as a redirect rather than a completed registration.

## 4. Verification and test matrix

- Unit tests: direct exam overlap, next-day exam, class overlap, low mock attendance, missing academic data, and time-zone boundaries.
- Authorization tests: students cannot read other students' academic-risk data; organizers cannot read student calendar, timetable, attendance, or warnings.
- Registration tests: unpublished events are hidden; internal registration creates `REGISTERED`; external registration creates `REDIRECTED_TO_EXTERNAL_REGISTRATION`.
- UI tests: warnings are advisory, the student can cancel, and organizer-only planning details are absent.
- Contract tests: risk type enums and registration states match `contracts/CONTRACTS.md`.

## 5. Overall definition of done

- [ ] The student event feed returns only published events visible to the requester.
- [ ] The Core API produces private deterministic warnings from synthetic mock data.
- [ ] Internal and external registration modes are represented truthfully.
- [ ] No component treats a warning as a university attendance decision.
- [ ] Contract, unit, authorization, and UI tests pass.

## 6. Risks and deviation log

- Attendance thresholds and attendance eligibility rules are not established. The MVP must use advisory language only.
- Google Calendar integration is optional after the mock flow works. It requires read-only OAuth consent, token security, and a fallback when no academic calendar is connected.
- 2026-10-10: Initial plan created from the approved student discovery, registration, timetable, and mock-attendance scope.
