# Amrita Coimbatore Facility Booking & Approval Workflow Guide

## Overview

This guide details the operational event proposal, facility booking, and two-stage institutional approval workflow for campus clubs at **Amrita Vishwa Vidyapeetham, Coimbatore Campus**.

---

## 1. Roles & Permissions

CampusCue implements a role-based access control (RBAC) hierarchy across the event lifecycle:

| Role | Entity Scope | Responsibilities | Review Authority |
|---|---|---|---|
| **Club Organizer** | Club (`memberships.club_id`) | Fill facility booking form, enclose Dean Academic Approval PDF, manage draft changes | None (Cannot self-approve) |
| **Faculty Advisor** | Club (`memberships.club_id`) | Conduct **Stage 1** review: verify faculty supervision, student participation, and academic alignment | **Stage 1 Approval** (`APPROVE`, `REJECT`, `REQUEST_REVISION`) |
| **Club Admin** | Club (`memberships.club_id`) | Club executive oversight, schedule coordination | None |
| **Campus Admin (OSA)** | Campus-wide (`campus_admin = true`) | Conduct **Stage 2 Final Review**, verify deterministic venue conflicts and 120-minute gap rules, record official evidence, and confirm booking | **Stage 2 Final Approval & Overrides** |
| **Student** | Campus-wide | Discover published events, view private academic-risk warnings, register | None |

---

## 2. Event Facility Booking Form (Official Coimbatore Campus Format)

The Plan Event page (`/plan`) maps directly to the official Amrita Vishwa Vidyapeetham Events Department Facility Booking Form (Rev. 15-Nov-24, Pages 24–26):

1. **Name of the Event:** 1–200 character string.
2. **Dept / Club Organizing the Event:** Bound to active club context.
3. **Date(s) & Timings:** Normalized start/end times in `Asia/Kolkata` (UTC+05:30).
4. **Organizing Secretary / Faculty / Staff Responsible:** Phone number and name of responsible mentor.
5. **Approximate Number of Participants:**
   - National (Male / Female)
   - International (Male / Female)
   - Auto-calculated attendance total.
6. **Academic Approval Copy from Dean of School:** Enclosed PDF uploaded directly to MinIO proposal storage.
7. **Hall(s) Required for the Event:**
   - Primary venue evaluated against deterministic scheduling engine.
   - Additional parallel halls: *New Auditorium / Pandal*, *Amriteswari Hall*, *Sudhamani Hall*, *Seminar Halls I & II*, *Acharya Hall / AB-1*, *Sandeepani Hall / AB II*, *Anugraha Hall AB III*.
8. **Other Campus Infrastructure:** Playground, parking, common halls.
9. **Audio / Video / Visual Requirement:** Projectors, mics, sound systems.
10. **Requirement of Food & Refreshments Table:** Dynamic date rows with Breakfast, Tea @ 11 AM, Tea @ 3 PM, Lunch, Dinner, and headcounts.
11. **Vehicle Requirements:** Requisitions for buses, vans, or staff cars.
12. **Guest Rooms & Hostel Rooms:** Guest House (AC), Annexe (AC), Boys Hostel, Girls Hostel.
13. **Publicity:** Flex at Main Gate, Flex at Venue, Digital Backdrop, Photography/Videography by AOC, Media Coverage by AOC.
14. **Funding of the Event:** University funded, external grant/sponsorship, registration fees, or seed grant.
15. **Additional Requirements & Abstract:** VIP protocols, security, program abstract.

---

## 3. Two-Stage Approval Pipeline

```
[Club Organizer]
       │
       ▼
Fills Form & Uploads Dean Approval PDF
       │
       ▼ (Status: SUBMITTED)
[Faculty Advisor (Stage 1)] ──► Checks Faculty Review Queue in /changes
       │
       ▼ (Approves Proposal)
[Campus Admin / OSA (Stage 2)] ──► Evaluates Deterministic Conflicts & Evidence
       │
       ├─► CONFIRMED: Event officially scheduled; Proposal indexed to RAG (CHUNKED)
       └─► OVERRIDE REQUIRED: Administrator records scoped exception (e.g. CAMPUS_GAP)
```

---

## 4. Grounded Policy Knowledge & RAG Ingestion

- **Approved Corpus:** Amrita Vishwa Vidyapeetham Student Affairs Handbook.
- **Storage:** ChromaDB persistent vector collection (`campus_policy_corpus`).
- **Retrieval:** Hybrid sparse (lexical) and dense semantic search with reciprocal rank fusion (RRF).
- **Attribution Invariant:** Answers cite exact page numbers and excerpts from the handbook. AI never fabricates approval status or venue availability.
