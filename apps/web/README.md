# CampusCue web

Next.js frontend for the Core API gateway. Browser requests use same-origin `/api/v1`; Next rewrites to server-only `CORE_API_URL` (default `http://127.0.0.1:8000`). Configure this value before building a production image because rewrites are compiled into the build.

## Local demo

From the repository root:

```powershell
docker compose --env-file .env.example up -d --build postgres migrate minio minio-init core-api agent-api web
docker compose --env-file .env.example exec core-api python -m scripts.seed_demo
```

Open http://localhost:3000. Use the profile menu with `organizer@example.invalid`, `club-admin@example.invalid`, or `campus-admin@example.invalid`. These are synthetic identities. Seeds add a club and two venues with UNKNOWN availability and do not create official bookings. Use the organizer to save a draft, propose it, and submit it; use the campus administrator to confirm the recorded schedule with evidence. Core checks all writes again.

The fake Agent provider is the default and may abstain. Real policy answers need the RAG service with approved indexed sources and a configured model provider. RAG model downloads are substantial; see the repository RAG guide.

Proposal PDFs use MinIO with private buckets; download links expire after 15 minutes. `MINIO_PUBLIC_ENDPOINT` must be browser reachable (localhost:9000 for a local demo). Regenerate links after expiration. Proposal review remains subject to Core authorization and RAG availability.

## Development and verification

Run in `apps/web`:

```powershell
npm ci
npm run dev
npm run lint
npx tsc --noEmit
npm test
npx playwright install chromium
npx playwright test --workers=2
npm run build
```

Browser tests render real pages with explicit synthetic HTTP contract fixtures; they do not prove that PostgreSQL, MinIO, or model providers are healthy. Core integration tests and a live gateway smoke check cover those boundaries separately.

Generate wire types from committed OpenAPI using Core's Python environment from the repository root:

```powershell
.\services\core-api\.venv\Scripts\python.exe apps/web/scripts/export_types.py --check
```

Reports are editable local drafts assembled from recorded facts; actual outcomes remain explicit placeholders. Schedule change previews are advisory and do not save edits. Core does not yet expose commitment or dependency-impact APIs. Unsupported assistant action types cannot be executed from the UI. Notification delivery is not implemented.
