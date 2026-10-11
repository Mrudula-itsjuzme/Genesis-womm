# CampusCue Official Source Registry

**Status:** Proposed allowlist for the demo ingestion pipeline
**Pilot:** Amrita Vishwa Vidyapeetham, Coimbatore
**Last checked:** 2026-10-10

## 1. Purpose and boundary

CampusCue uses two separate ingestion paths. Policy and procedure documents go to the RAG service for cited answers. Structured campus data goes to PostgreSQL for event discovery, resource exploration, club discovery, services, and calendar views. These paths must not be collapsed into one vector index.

Every stored record must retain `source_url`, `source_id`, `collected_at`, `last_checked_at`, parser version, content hash when available, source timestamp when published, extraction status, and confidence or review state. A source record is provenance, not evidence that a venue is available or an event is institutionally approved.

The listed endpoints returned HTTP 200 during the 2026-10-10 access check. That confirms retrieval at that time only. The scraper must still follow `robots.txt`, terms, published rate limits, and access controls. It must not bypass authentication.

## 2. Policy and procedure pipeline: RAG

Only approved policy or procedural documents enter the RAG corpus. Chunks retain document version, page or section path, exact source URL, access level, and verification timestamp. RAG answers must cite retrieved evidence and abstain when the material does not support an answer.

| Source ID | Source | URL | Extract for RAG | Treatment |
|---|---|---|---|---|
| `osa_handbook_cbr` | OSA Student Affairs Handbook | https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf | Event SOPs, club procedures, approval inputs, facility-booking format, reporting requirements | PDF parser; preserve page and heading metadata; highest first-ingestion priority |
| `student_affairs_welfare` | Student Affairs and Welfare | https://intranet.cb.amrita.edu/students-affairs-welfare | Published club-oversight and event-organization guidance | HTML parser; require review before activating as policy corpus because page content can change |

The handbook is an especially useful first source because it includes student-event procedures, facility-request material, and an activity-report example. Its policies describe procedures, not automated approvals or live facility availability.

## 3. Structured operational pipeline: PostgreSQL

Structured sources produce normalized records, each linked to a source record and a source-specific freshness state. The source parser must not promote a published calendar entry into a confirmed booking. Missing data or a blank feed remains `UNKNOWN`, never available.

| Source ID | Source | URL | Structured records | Parser and freshness rule |
|---|---|---|---|---|
| `campus_events` | Coimbatore campus events | https://intranet.cb.amrita.edu/events | Published event title, date/time when present, venue, description, organizer details when published | HTML extractor; event-discovery source only, not a booking feed |
| `academic_calendar` | Academic calendar and timetables | https://intranet.cb.amrita.edu/academics/calendar | Academic dates, exams, holidays, published calendar links | HTML extractor; calendar source, not an individual student timetable without an authorized connection |
| `campus_ics_calendar` | Official iCalendar feed | https://outlook.office365.com/owa/calendar/c5368a2f38a14425b7bfe0806e6a7242@amrita.edu/c90d8c3dd3654d4fa7af29ce6c6319907829757625615220928/calendar.ics | Calendar entries, UID, start/end, title, recurrence and last-modified fields when present | ICS parser; upsert by source plus UID; preserve recurrence and source update metadata |
| `campus_infrastructure` | Coimbatore infrastructure directory | https://www.amrita.edu/campus/coimbatore/infrastructure/ | Facilities, buildings, accommodation, sports spaces and amenities | HTML extractor; resource catalog only, no availability inference |
| `icts_services` | ICTS infrastructure and services | https://intranet.cb.amrita.edu/infrastructure/icts | AV support, computing facilities, helpdesk and technical services | HTML extractor; service catalog with reviewable freshness |
| `icts_support_contacts` | ICTS support contacts | https://intranet.cb.amrita.edu/infrastructure/icts/support-contacts | Published service routing, support categories and official department contact channels | HTML extractor; retain only published departmental contact channels; do not collect unnecessary personal data |

## 4. Discovery and lower-freshness sources

These pages are useful for club and activity discovery. They can contain historical material. Their extracted records require a `REVIEW_REQUIRED` operational-freshness state until a current date, status, and campus relevance are established. Do not create current event records solely from undated or historical club-page text.

| Source ID | Source | URL | Collect |
|---|---|---|---|
| `campus_home` | Coimbatore intranet homepage | https://intranet.cb.amrita.edu/ | Published announcements, upcoming-event notices and links |
| `iic_events_2026` | Institution's Innovation Council calendar | https://intranet.cb.amrita.edu/events/2026/IIC | Innovation activities and planned event records with published dates |
| `life_at_amrita` | Life at Amrita | https://www.amrita.edu/life-at-amrita/ | General club names and descriptions; do not assume all content is Coimbatore-specific |
| `computing_student_corner` | School of Computing student corner | https://www.amrita.edu/school/computing/coimbatore/student-corner/ | Technical clubs and published activities |
| `asb_student_clubs` | ASB student clubs | https://www.amrita.edu/school/business/coimbatore/activities/studentclub/ | Club descriptions and published activities |
| `arya_club` | ARYA club | https://www.amrita.edu/campus/coimbatore/students-club/arya/ | Club description, activities and historical calendar references |
| `raagasudha_club` | Raagasudha | https://www.amrita.edu/campus/coimbatore/students-club/raagasudha/ | Music-club description and published activities |
| `intel_iot_club` | Intel IoT Club | https://www.amrita.edu/campus/coimbatore/students-club/intel-iot-club/ | Workshop history and venue references |
| `team_media` | Team Media | https://www.amrita.edu/campus/coimbatore/students-club/team-media/ | Club activities and media-support context |
| `student_energy` | Student Energy | https://www.amrita.edu/campus/coimbatore/students-club/student-energy/ | Sustainability-club information and published activities |

## 5. Normalized storage and provenance

The structured pipeline writes source-backed records to PostgreSQL:

- `source_documents` or `source_fetches`: source identity, URL, response metadata, content hash, retrieval timestamps, parse result, access class and freshness state.
- `events`: source event identifier, title, interval when published, venue text, organizer text when published, canonical source link and status such as `PUBLISHED`, `HISTORICAL`, or `REVIEW_REQUIRED`.
- `academic_calendar_entries`: source UID or stable key, date interval, category, recurrence metadata, source version and review state.
- `resources` and `services`: normalized name, category, description, responsible office, restrictions, official channel and source link. Their availability is `UNKNOWN` unless authorized evidence says otherwise.
- `clubs`: normalized name, campus scope, description, source URL and `last_verified_at`.

Deduplicate with source-specific stable identifiers first, such as ICS UID. Use normalized title, date, and venue only as a review cue, never as a reason to silently merge uncertain records.

## Private identities, proposals and shared-resource access

- **Public policy retrieval is allowlist-only.** It may index reviewed institutional rules and public procedures; it must not index student timetables, grades, attendance, registration records, faculty-private information, personal contact details, event proposal PDFs or access credentials.
- **Private proposal PDF ingestion/search is disabled** in the RAG API until authenticated service-to-service identity, resource-owner authorization, club-scoped query enforcement, audit logging and retention/deletion rules are implemented and verified. Approval of a PDF is **not** permission to publish or index it.
- Existing deployments that previously indexed proposal PDFs must separately audit and delete those private chunks, because disabling new ingestion does not erase historical index data.
- Publicly listed departmental support channels may be displayed as sourced structured records; do not promote named personal faculty/student contacts into general retrieval without an explicit lawful, reviewed basis.
- Shared-resource planning (HPC/GPU time, labs, AV equipment) records **interest**, not allocations. It never reveals user identifiers, quota usage, credentials or private workload data to a public search corpus.

## 6. Source safety rules

- Do not collect student registration lists, roll numbers, personal phone numbers, or other unnecessary personal data.
- Do not use a public calendar or event page as proof of real-time facility availability.
- Keep tentative interest, official bookings, and unknown availability as separate states.
- Recheck official data on a scheduled cadence and label stale or parse-failed records.
- Store raw source snapshots only when retention and access policy permit. Otherwise store the permitted extracted fields, provenance, and content hash.
- Keep policy documents in the reviewed RAG allowlist. Keep event, calendar, facility, service, and club records in structured storage.

## 7. First demo ingestion order

1. OSA handbook PDF.
2. Campus events page.
3. Academic calendar page and ICS feed.
4. ICTS services and support contacts.
5. Coimbatore infrastructure directory.
6. Student Affairs and Welfare page after content review.
7. Homepage, IIC, and club pages after the core pipeline is reliable.

This order supports the demo resource explorer, policy assistant, published-event discovery, calendar context, and service routing without claiming institutional integrations that are not available.
