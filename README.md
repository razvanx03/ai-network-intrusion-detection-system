# AI Network Intrusion Detection System (NIDS)

An AI NIDS platform for manually importing and preparing Zeek connection metadata (`conn.log`). Durable analysis sessions track progress, source records and failures. No detector is configured: preparation does not assess traffic safety and generates no alerts. Other Zeek log types are not implemented.

---

## Features

- **Replaceable AI boundary**: Typed, model-independent input and finding contracts; no model, training, inference or feature vector is selected yet.
- **Traceable sessions**: Durable status, per-batch counts, normalized source references and future finding evidence. Existing demonstration alerts are preserved and explicitly labelled as demo history.
- **Zeek Metadata Analysis**: Inspects session-level telemetry (duration, packet ratios, byte counts, TCP connection states such as `S0`, `REJ`, `SF`) without requiring deep packet payload decryption.
- **Live Operations Console**: Real-time web dashboard to fetch & analyze Zeek logs from a remote sensor agent (or local simulation generator), filter alerts by severity, inspect raw network connections by protocol (`TCP`, `UDP`, `ICMP`), and manage sensor/database state.
- **Secure Authentication**: Single-admin authentication backed by `bcrypt` password hashing and `HttpOnly` JWT cookies with strict CORS protection.
- **Fail-Fast Configuration**: Strict environment validation on both backend and frontend — missing or invalid configuration causes an immediate, descriptive startup error.
- **Bilingual & Themeable UI**: Instant switching between Romanian and English (`ro` / `en`) and Dark / Light themes (`dark` / `light`).

---

## Project Architecture

```text
ai-network-intrusion-detection-system/
├── api/                          # Backend: Python + FastAPI + SQLAlchemy 2.0
│   ├── app/
│   │   ├── ai/                   # Model-independent preparation & replaceable detector contract
│   │   ├── core/                 # Strict .env settings, JWT HttpOnly cookie security, bcrypt
│   │   ├── database/             # Database engine, session management, initial admin seeder
│   │   ├── integrations/         # Remote Zeek Sensor HTTP client & mock telemetry generator
│   │   ├── models/               # SQLAlchemy entities, sensor cursors & analysis-session evidence
│   │   ├── repositories/         # Data access layer isolating database queries
│   │   ├── routes/               # REST API controllers, including /analysis-sessions
│   │   ├── schemas/              # Pydantic request/response DTOs
│   │   └── services/             # Core business logic & AI analysis orchestration
│   ├── data/samples/             # Sample Zeek connection telemetry datasets
│   ├── migrations/               # Alembic database migrations
│   └── requirements.txt
├── app/                          # Frontend: React 19 + TypeScript + Vite + Tailwind CSS v4 + shadcn/ui
│   ├── src/
│   │   ├── components/           # ProtectedRoute & shadcn/ui primitives (Card, Table, Badge, etc.)
│   │   ├── contexts/             # AuthContext (HttpOnly session state management)
│   │   ├── layouts/              # AppLayout (Navigation bar, sensor status, user controls)
│   │   ├── pages/                # File-based routes (/dashboard, /connections, /login)
│   │   ├── services/             # Fetch API client with credentials support
│   │   ├── constants.ts          # Strict environment variable validation
│   │   └── i18n.tsx              # Centralized RO/EN translations & theme provider
│   └── package.json
├── sensor_agent/                 # Edge Collector: Lightweight daemon running on the Zeek VM
│   ├── collector.py              # Incremental log reader & authenticated REST API
│   ├── install_zeek.sh           # Automated Zeek installation script for Ubuntu/Debian
│   ├── requirements.txt          # Minimal Python dependencies (FastAPI, uvicorn)
│   └── README.md                 # Standalone setup and deployment guide for the VM
├── .env                          # Local environment configuration (git-ignored)
└── .env.example                  # Environment configuration template
```

---

## Prerequisites

- **Python** 3.11+
- **Node.js** 20+ and **npm**

---

## Configuration

1. Copy `.env.example` to `.env` in the root directory:
   ```bash
   cp .env.example .env
   ```
2. Review and adjust the variables in `.env`:
   - `SECRET_KEY` — Secret key for signing JWT tokens (minimum 32 characters).
   - `ADMIN_USERNAME` / `ADMIN_PASSWORD` — Initial administrator credentials seeded at startup.
   - `DATABASE_URL` — SQLAlchemy connection string (e.g., `sqlite:///./data/nids.db` or PostgreSQL URI).
   - `CORS_ORIGINS` — JSON array of allowed frontend origins (e.g., `["http://localhost:5173","http://127.0.0.1:5173"]`).
   - `SENSOR_MOCK_MODE` — Set to `True` to use the built-in Zeek traffic simulator, or `False` to poll a live remote Zeek VM sensor agent at `SENSOR_AGENT_URL`.
   - `VITE_API_BASE_URL` — Base API path used by the frontend (e.g., `/api`).

---

## How to Run

### 1. Start the Backend API

Open a terminal in the `api/` directory:

```powershell
cd api
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --port 8000
```

> If the virtual environment does not exist yet, create it and install dependencies first:
> ```powershell
> python -m venv .venv
> .\.venv\Scripts\Activate.ps1
> pip install -r requirements.txt
> ```

- **API Base URL**: `http://localhost:8000/api`
- **Interactive Swagger Docs**: `http://localhost:8000/docs`

### 2. Start the Frontend Application

Open a second terminal in the `app/` directory:

```bash
cd app
npm install
npm run dev
```

- **Web Application**: `http://localhost:5173` (automatically redirects to `/dashboard` or `/login`)

---

## Usage

1. Sign in at `http://localhost:5173/login` using the administrator credentials configured in `.env`. The login form does not prefill credentials.
2. On the **Live Dashboard** (`/dashboard`):
   - Click **Fetch & Analyze Logs** to pull the latest Zeek connection flows from the sensor, create a session, import and normalize new records, and display session status and source connections. Detection remains explicitly unavailable until a real detector is configured.
   - Filter security alerts by severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and mark investigated alerts as resolved.
   - Use **Reset sensor cursor** to restart reading existing sensor logs (the log file is not deleted) or **Reset DB** to clear stored connections, alerts and analysis history. Sensor cursors are retained until separately reset.
3. Navigate to **Zeek Flows** (`/connections`) to inspect raw network sessions, connection states (`SF`, `S0`, `REJ`), durations, byte counts, and packet ratios filtered by protocol (`TCP`, `UDP`, `ICMP`).
## Platform boundaries

- All alert, connection and system endpoints require an active administrator session. Login returns user and session metadata; the JWT is transmitted only in an HttpOnly cookie.
- Set secure-cookie options appropriately for deployment over HTTPS. Local HTTP development must use an explicit compatible configuration.
- The dashboard supports paginated alerts and connections, visible request errors, and Romanian/English themes and labels. Alert exports include all records matching the selected severity, not just the visible page.
- `api/app/ai/engine.py` defines the detector contract. The current implementation is explicitly unconfigured and emits no findings. Replace only that implementation when a validated detector is ready; the transport and frontend do not depend on a specific model.
- The VM collector discovers current JSON conn.log streams and retained gzip archives. The backend commits each file cursor together with connections and alerts in SQLite, resumes across rotation, and analyzes only new connection UIDs. Retain unread archives until ingestion. Deploy the updated backend and sensor together. See [sensor setup and recovery](sensor_agent/README.md).
- Sensor mode describes configuration, not a live VM connectivity probe.
- Source files under `app/src/lib/` must be included when committing the frontend. Python environment directories remain ignored.

## Verification

Run `npm run build` and `npm run lint` from `app/`. Validate login/logout, expired sessions, protected API requests, pagination, error recovery, exports, theme/language persistence and mobile navigation manually. No automated test suite is included.

## Analysis architecture and API

The manual path is routes -> AnalysisService -> IngestionService -> normalization
and model-independent preparation -> detector contract -> repositories. The sensor
transport, authentication, archive discovery, UID deduplication and per-batch cursor
commits retain their existing behavior. No background ingestion or inference runs.

- `POST /api/system/fetch-and-analyze` remains the dashboard command. Its existing
  summary fields are retained and `analysis_session` is added.
- `POST /api/analysis-sessions` accepts `{"source":"sensor"}` or
  `{"source":"stored","connection_ids":[1,2]}` (1..500 existing IDs).
  Stored analysis explicitly reuses records without copying raw logs or moving cursors.
- `GET /api/analysis-sessions?limit=20&offset=0` lists history; `GET /{id}` retrieves
  status, counters, detector/preparation metadata and safe error codes.
- `GET /api/analysis-sessions/{id}/connections` and `/alerts` return paginated
  source records and findings. `/alerts/{alert_id}/connections` returns exact evidence,
  including multiple connections for a future aggregate finding.
- All endpoints require the existing admin cookie. Failures return a safe code and
  session ID; credentials and remote response bodies are never sent to the frontend.

Sessions are request-driven and use **one API worker**. A database constraint rejects
concurrent analysis; reset operations refuse while a session is running. Restarting
the API marks unfinished sessions interrupted. Resume is manual: committed batches
remain saved and unread batches are fetched again. There is no durable job queue or
automatic retry. Add such infrastructure only if long-running inference later needs it.

`records_prepared` counts newly imported records (or explicitly selected stored IDs),
not a security verdict. For each batch, connections, source links, future findings,
counts and cursor advancement commit together. A malformed record or failed detector
rolls back that batch and marks the session failed; earlier committed batches survive.
Future detectors must return typed findings referencing only their batch's connection
IDs. Detection categories, feature vectors, time windows, datasets and model choice
remain undecided. The existing transport batch size is not a chosen analysis window.

## Database evolution

Startup retains the existing `create_all` bootstrap and applies Alembic revision
`7b9c0d1e2f30` after the original empty baseline. It adds `analysis_sessions`,
`analysis_session_connections`, `alert_connections`, and alert session/provenance
columns. Existing connections, sensor cursors and alerts are preserved; pre-existing
alerts are labelled `legacy_demo`. No raw logs are duplicated. The migration is additive and idempotent with the existing bootstrap;
restore a database backup for rollback rather than discarding analysis history.

## Implementation file map

Files added for session-based preparation:

- `api/app/ai/preparation.py`: typed model-independent preparation.
- `api/app/services/ingestion_service.py`, `api/app/services/analysis_service.py`: ingestion and session orchestration.
- `api/app/models/analysis_session.py`, `api/app/repositories/analysis_repository.py`: sessions and source/finding evidence.
- `api/app/schemas/analysis.py`, `api/app/routes/analysis_routes.py`: session contracts and protected endpoints.
- `api/app/database/schema.py`, `api/migrations/versions/7b9c0d1e2f30_analysis_sessions.py`: schema bootstrap/evolution.
- `app/src/components/dashboard/analysis-sessions.tsx`: session status, history and paginated source records/results.

Existing integration files updated:

- `api/app/ai/engine.py`: replaceable, explicitly unconfigured detector. The old synthetic detector module `api/app/ai/detector.py` was removed.
- `api/app/main.py`, `api/app/database/seed.py`, `api/migrations/env.py`, `api/app/models/__init__.py`: startup, migration registration and interruption recovery.
- `api/app/models/alert.py`, `api/app/repositories/alert_repository.py`, `api/app/repositories/connection_repository.py`: provenance, evidence and transactional resets.
- `api/app/schemas/alert.py`, `api/app/schemas/connection.py`, `api/app/schemas/system.py`: validation and compatible response extensions.
- `api/app/routes/system_routes.py`, `api/app/services/system_service.py`, `api/app/services/alert_service.py`: existing command compatibility, reset safety and export provenance.
- `app/src/components/dashboard/commands.tsx`, `app/src/components/dashboard/alerts.tsx`, `app/src/pages/dashboard.tsx`: detector availability, historical-demo labels and session integration.
- `app/src/services/api.ts`, `app/src/services/types.ts`, `app/src/i18n.tsx`: typed API integration and RO/EN text.
- `api/requirements.txt`: removed unused detection-library requirements; no new dependencies.
- `README.md`: current architecture, lifecycle, API and file map.
