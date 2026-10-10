# CampusCue Project Brief

## One-line definition
CampusCue is an AI-assisted event operations workspace that helps university clubs plan early, coordinate clearly, and understand what actually changed.

## Pilot and status
- Pilot campus: Amrita Vishwa Vidyapeetham, Coimbatore.
- Stage: idea and planning; no institutional integration is assumed.
- Primary use case: club event planning and operations before and after official approval.

## Users
- Club organizers: create proposals, discover resources, track requests, manage event dependencies, prepare reports.
- Club committee members: coordinate tasks and handovers within authorized visibility.
- Authorized campus administrators: verify institutional status and apply explicitly permitted overrides, if the pilot authorizes this role.
- Incoming committee members: use approved, sanitized operational memory.

## Problem
Event information is fragmented across handbooks, campus websites, forms, emails, conversations and previous organizers. Organizers struggle to identify tentative scheduling clashes, distinguish acknowledgments from approvals, coordinate changes, track follow-ups, and close post-event obligations.

## Product promise
Make organizer-controlled work easier without pretending to remove institutional approval delays or replace official systems.

## Core features
1. Tentative event proposals and cross-club overlap visibility.
2. Sourced campus resource explorer with verification metadata.
3. OSA handbook assistant using hybrid RAG and page citations.
4. Commitment and evidence tracking.
5. Deterministic scheduling conflict detection.
6. Change-impact analysis across tasks and commitments.
7. Editable event and monthly reports with missing fields flagged.
8. Approved operational memory and committee handover support.

## Differentiation
The product's focus is event operational memory: what is planned, what is evidenced, what depends on what, what changed, and what remains open. The signature demonstration is a mid-planning event change, not a disconnected feature tour.

## Trust and status vocabulary
- **Tentative:** organizer intent, not a reservation.
- **Requested/Submitted:** request sent or submission recorded; not confirmation.
- **Acknowledged:** receipt acknowledged; not necessarily acceptance.
- **Conditionally confirmed:** confirmation subject to stated conditions.
- **Confirmed:** supported by authorized evidence.
- **Needs revalidation:** a prior commitment may no longer apply after a change.
- **Unknown availability:** no authoritative availability source is available.
- **Closed:** a commitment or task is complete, with evidence where appropriate.

## Constraints
- Never infer venue availability from an empty calendar.
- Never infer official approval from organizer-reported status.
- Never let the LLM own scheduling truth or authorization.
- Never invent report facts, source citations, attendance, photos, speakers, reimbursements, or acknowledgments.
- Do not ingest private organizer-group exports or private conversations into public/general RAG.
- No automatic external messages or official status changes in MVP.
- Synthetic demo data must be labeled as synthetic.

## Success criteria
- Correctly identify event overlaps and two-hour-gap violations according to the configured rule.
- Correctly distinguish tentative, requested, acknowledged and confirmed states.
- RAG returns relevant source excerpts and correct page citations.
- Agent chooses appropriate tools and reports tool outcomes accurately.
- Venue/time changes identify relevant downstream dependencies with low false-alarm rates.
- Reports contain verified facts and visibly flag missing data.
- A pilot can compare manual versus CampusCue time for planning or closure tasks without making unsupported claims about approval-time reductions.

## Out of scope
CampusCue is not the official booking authority, a generic chatbot, a public directory of private club information, or an automatic approval engine. Live booking integration requires explicit authorization and an existing approved source.
