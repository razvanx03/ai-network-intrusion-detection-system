# AI Network Intrusion Detection System (NIDS)

An AI Network Intrusion Detection System (NIDS) platform prepared to analyze Zeek network flow metadata (`conn.log`) with a demonstration detector for port scans, repeated SSH connections, traffic bursts, and statistical anomalies. The current detector uses a synthetic baseline; its results are illustrative, not validated threat classifications. Other Zeek log types are not implemented.

---

## Features

- **Demonstration AI Detection Engine**: Combines behavioral heuristic analysis with unsupervised anomaly detection (`IsolationForest` via `scikit-learn`) over extracted flow feature vectors.
- **Demonstration MITRE ATT&CK Mapping**: Labels demonstration alerts with MITRE ATT&CK technique identifiers (`T1046` Network Service Scanning, `T1110` Brute Force, `T1498` Network Denial of Service, `T1071` Application Layer Protocol Anomaly) and severity levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`).
- **Zeek Metadata Analysis**: Inspects session-level telemetry (duration, packet ratios, byte counts, TCP connection states such as `S0`, `REJ`, `SF`) without requiring deep packet payload decryption.
- **Live Operations Console**: Real-time web dashboard to fetch & analyze Zeek logs from a remote sensor agent (or local simulation generator), filter alerts by severity, inspect raw network connections by protocol (`TCP`, `UDP`, `ICMP`), and manage sensor/database state.
- **Secure Authentication**: Single-admin authentication backed by `bcrypt` password hashing and `HttpOnly` JWT cookies with strict CORS protection.
- **Fail-Fast Configuration**: Strict environment validation on both backend and frontend — missing or invalid configuration causes an immediate, descriptive startup error.
- **Bilingual & Themeable UI**: Instant switching between Romanian and English (`ro` / `en`) and Dark / Light themes (`dark` / `light`).

---

## Project Architecture

```text
ai-network-intrusion-detection-system/
├── api/                          # Backend: Python + FastAPI + SQLAlchemy 2.0 + scikit-learn
│   ├── app/
│   │   ├── ai/                   # Feature extractor, heuristics & IsolationForest AI detector
│   │   ├── core/                 # Strict .env settings, JWT HttpOnly cookie security, bcrypt
│   │   ├── database/             # Database engine, session management, initial admin seeder
│   │   ├── integrations/         # Remote Zeek Sensor HTTP client & mock telemetry generator
│   │   ├── models/               # SQLAlchemy ORM models (User, Connection, Alert)
│   │   ├── repositories/         # Data access layer isolating database queries
│   │   ├── routes/               # REST API controllers (/auth, /logs, /alerts, /system)
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
   - Click **Fetch & Analyze Logs** to pull the latest Zeek connection flows from the sensor, run the AI detection pipeline, store flows and alerts in the database, and update the dashboard metrics in real time.
   - Filter security alerts by severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and mark investigated alerts as resolved.
   - Use **Reset sensor cursor** to restart reading existing sensor logs (the log file is not deleted) or **Reset DB** to clear all stored connections and alerts.
3. Navigate to **Zeek Flows** (`/connections`) to inspect raw network sessions, connection states (`SF`, `S0`, `REJ`), durations, byte counts, and packet ratios filtered by protocol (`TCP`, `UDP`, `ICMP`).
## Platform boundaries

- All alert, connection and system endpoints require an active administrator session. Login returns user and session metadata; the JWT is transmitted only in an HttpOnly cookie.
- Set secure-cookie options appropriately for deployment over HTTPS. Local HTTP development must use an explicit compatible configuration.
- The dashboard supports paginated alerts and connections, visible request errors, and Romanian/English themes and labels. Alert exports include all records matching the selected severity, not just the visible page.
- `api/app/ai/engine.py` defines the analysis interface. The existing demonstration engine is its current implementation; replace it when the real AI is ready.
- The VM collector uses durable batches acknowledged after database commit. Retries analyze only new connection UIDs. Retained JSON/TSV conn.log files and gzip archives are supported; unread archives must not be deleted before ingestion. Deploy the updated backend and sensor together. See [sensor setup and recovery](sensor_agent/README.md).
- Sensor mode describes configuration, not a live VM connectivity probe.
- Source files under `app/src/lib/` must be included when committing the frontend. Python environment directories remain ignored.

## Verification

Run `npm run build` and `npm run lint` from `app/`. Validate login/logout, expired sessions, protected API requests, pagination, error recovery, exports, theme/language persistence and mobile navigation manually. No automated test suite is included.
