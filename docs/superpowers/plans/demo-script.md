# CampusCue: 3-Minute Live Hackathon Pitch Script & Presenter Runbook

> **Target Audience:** Hackathon Judges & Evaluators  
> **Duration:** Strictly 3 minutes (180 seconds)  
> **Environment:** Offline-resilient local demo (`http://localhost:3000`, Amrita Coimbatore pilot data)

---

## ⏱️ Timing Breakdown

| Time | Phase | Screen / URL | Key Message |
|---|---|---|---|
| **0:00 – 0:30** | The Problem | Intro / Slide | Campus event chaos: conflicting bookings, unverified approvals, lost paperwork |
| **0:30 – 1:00** | Screen 1: Calendar | `/calendar` | Status Honesty: Tentative proposal ≠ Confirmed booking; color-coded intervals |
| **1:00 – 1:30** | Screen 2: Conflict Engine | `/plan` | Real-time interval checks, 120-min campus gap rule, instantaneous conflict advice |
| **1:30 – 2:00** | Screen 3: Change Impact | `/changes` | Downstream impact analysis: schedule shifts, equipment dependencies, revision tracking |
| **2:00 – 2:30** | Screen 4: Grounded AI | `/policy` | Bounded AI assistant with real evidence citations and human-in-the-loop action drafts |
| **2:30 – 3:00** | Screen 5: Storage & Reports | `/reports` | Secure MinIO proposal archive, one-click report generator, concluding pitch |

---

## 🎙️ Spoken Script & Click-by-Click Actions

### 1. The Hook & The Problem (0:00 – 0:30)
> *"Every university club organizer knows the dread of campus event planning: you spend weeks planning a robotics workshop, print posters, and on event day, another club has booked your auditorium, your projector request was lost in an email chain, and faculty approvals were never verified.*
>
> *Existing college portals are static forms or empty calendars. But **an empty calendar does not mean a venue is available.** Welcome to **CampusCue**—the AI-assisted operations workspace built for university clubs."*

---

### 2. Screen 1: Unified Campus Calendar & Status Honesty (0:30 – 1:00)
**Action:** Open `http://localhost:3000/calendar`.
- Point to the **Status Guide**: Green (Confirmed), Amber (Tentative Proposal), Blue (Draft), Gray (Cancelled).
- Click on any event to trigger the **Event Detail Modal**.

> *"First, our Core Source of Truth: the Unified Campus Calendar. Notice the green confirmed bookings versus amber tentative proposals.*
>
> *CampusCue enforces a strict product law: **A tentative event proposal is not a venue booking.** Organizers can immediately see confirmed commitments and tentative hold requests with half-open intervals in Asia/Kolkata campus time."*

---

### 3. Screen 2: Real-Time Conflict Detection (1:00 – 1:30)
**Action:** Click **"Plan an event"** (or navigate to `/plan`).
- Select **Synthetic Main Auditorium**.
- Enter Date: `2026-11-20`, Start: `10:00`, End: `11:00`.
- Watch the **Scheduling Advice** sidebar update dynamically.

> *"Now let's plan a new event. As I choose the Main Auditorium on November 20th, notice the right sidebar:*
>
> *CampusCue immediately executes a transactional interval check against Core API:*
> 1. *It catches a **VENUE_OVERLAP** with an existing guest lecture.*
> 2. *It warns about the **120-minute campus-wide gap rule**.*
>
> *Instead of silently allowing a double-booking or failing at submission time, the organizer gets instantaneous, actionable guidance."*

---

### 4. Screen 3: Downstream Change Impact Assessment (1:30 – 2:00)
**Action:** Navigate to `http://localhost:3000/changes`.
- Select an existing event from the dropdown.
- Point to the **Change Proposal Panel** and **Dependency Registry**.

> *"What happens when an event schedule shifts? In traditional universities, downstream coordinators—AV support, equipment kits, and security—are left in the dark.*
>
> *In CampusCue, every change is staged with revision tracking. Our deterministic engine computes the ripple effect across registered commitments: required revalidations, equipment overlaps, and faculty re-approvals."*

---

### 5. Screen 4: Grounded Policy Assistant with Citations (2:00 – 2:30)
**Action:** Navigate to `http://localhost:3000/policy`.
- Click the demo prompt chip: **"📅 Plan Robotics Workshop"**.
- Watch the response appear.
- Expand **"Tool activity"** to show `check_event_conflicts` and `file_event_draft_proposal`.
- Show the **"Confirm draft creation"** human-in-the-loop button.

> *"Here is CampusCue's Policy & Planning Assistant. But unlike hallucination-prone chatbots, our LLM operates under bounded orchestration:*
>
> *Notice it executed real tools: checking Core conflicts first, then filing a draft proposal.*
> *Crucially: **the AI never books the venue itself.** It drafts an action card marked `PROPOSED`, requiring explicit human authorization."*

---

### 6. Screen 5: Proposal Documents & Verified Reports (2:30 – 3:00)
**Action:** Navigate to `http://localhost:3000/reports`.
- Select an event to view the auto-generated report.
- Click **"Copy to clipboard"** or **"Export text"**.

> *"Finally, from proposal PDFs stored securely in MinIO object storage with presigned expiring URLs, to post-event reporting:*
>
> *CampusCue automatically compiles verified event facts—actual timings, venue details, and commitments—into editable report drafts ready for administration submission.*
>
> *CampusCue replaces chaos with clarity, ensuring university events run smoothly from ideation to post-event reporting. Thank you!"*

---

## 🛠️ Pre-Presentation Setup Checklist

Before presenting to judges:

1. **Containers Running:** Run `docker compose ps` to verify all 5 containers are up (`healthy`).
2. **Demo Mode Active:** Ensure `AGENT_DEMO_MODE=true` in `.env` (guarantees offline zero-network resilience).
3. **Smoke Verification:** Run `python scripts/demo_smoke.py` (ensure output ends with `All checks passed.`).
4. **Browser Tabs Pre-loaded:**
   - Tab 1: `http://localhost:3000/calendar` (logged in as `organizer@demo.invalid`)
   - Tab 2: `http://localhost:3000/plan`
   - Tab 3: `http://localhost:3000/changes`
   - Tab 4: `http://localhost:3000/policy`
   - Tab 5: `http://localhost:3000/reports`
