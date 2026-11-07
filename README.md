# AI Network Intrusion Detection System (NIDS)

AI NIDS collects Zeek connection metadata (`conn.log`) from a remote sensor and analyzes it when an administrator requests it. The selected Random Forest classifier, trained on a published Zeek-derived CIC-IDS2017 dataset, flags suspicious connections for review. A React dashboard displays connections, findings and traceable analysis sessions. See [AI experiments, results and reproduction](ai/README.md).

---

## Features

- **Replaceable AI boundary**: Typed input/finding contracts, shared versioned Zeek features and a locally selected classifier. Offline training compares Logistic Regression, Random Forest and Isolation Forest on TON_IoT Network and a Zeek-derived CIC-IDS2017 release.
- **Traceable sessions**: Durable status, per-batch counts, normalized source references and finding evidence. Existing demonstration alerts are preserved and explicitly labelled as demo history.
- **Connection classification**: Uses duration, directional byte/packet counts, protocol, detected service and connection state. Shared preprocessing preserves missing values and applies the same feature transformations during training and inference.
- **Operations dashboard**: Refreshes stored metrics and analysis status, provides a manual fetch-and-analyze command, severity filters, paginated connection records, alert exports and database/cursor management. An explicit sample mode reads bundled demonstration records.
- **AI review workflow**: Shows unique stored, analyzed and flagged connections, pending analysis, session counts and protocol distribution. Open a finding to inspect its model score and source connection; mark it as new, under investigation, resolved or false positive. Demo history is available separately and excluded from AI dashboard statistics.
- **Secure Authentication**: Single-admin authentication backed by `bcrypt` password hashing and `HttpOnly` JWT cookies with strict CORS protection.
- **Fail-Fast Configuration**: Strict environment validation on both backend and frontend — missing or invalid configuration causes an immediate, descriptive startup error.
- **Bilingual & Themeable UI**: Instant switching between Romanian and English (`ro` / `en`) and Dark / Light themes (`dark` / `light`).

---

## Project Architecture

```text
ai-network-intrusion-detection-system/
├── api/                          # Backend: Python + FastAPI + SQLAlchemy 2.0
│   ├── app/
│   │   ├── ai/                   # Shared features, replaceable detector & explicit model deployment
│   │   ├── core/                 # Strict .env settings, JWT HttpOnly cookie security, bcrypt
│   │   ├── database/             # Database engine, session management, initial admin seeder
│   │   ├── integrations/         # Remote Zeek Sensor HTTP client & bundled sample reader
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
│   │   ├── layouts/              # AppLayout (Navigation bar and user controls)
│   │   ├── pages/                # File-based routes (/dashboard, /connections, /login)
│   │   ├── services/             # Fetch API client with credentials support
│   │   ├── constants.ts          # Strict environment variable validation
│   │   └── i18n.tsx              # Centralized RO/EN translations & theme provider
│   └── package.json
├── ai/                           # Offline acquisition, preparation, experiments and measured reports
├── sensor_agent/                 # Edge Collector: Lightweight daemon running on the Zeek VM
│   ├── collector.py              # Incremental log reader & authenticated REST API
│   ├── setup_vm.sh               # Unified Ubuntu gateway, Zeek, capture and sensor setup
│   ├── requirements.txt          # Minimal Python dependencies (FastAPI, uvicorn)
│   └── README.md                 # Standalone setup and deployment guide for the VM
├── .env                          # Local environment configuration (git-ignored)
└── .env.example                  # Environment configuration template
```

---

## Prerequisites

- **Python** 3.13 recommended for the pinned AI environment
- **Node.js** 20.19+ in the 20.x line, or 22.12+ (matching the installed Vite requirement), and **npm**

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
   - `SENSOR_MOCK_MODE` — Set to `True` to read bundled demonstration records, or `False` to fetch from the remote sensor when analysis is requested. A remote failure does not switch to sample mode.
   - `SENSOR_AGENT_URL` / `SENSOR_AGENT_API_KEY` — Sensor address and shared API key, matching the sensor's own configuration.
   - `VITE_API_BASE_URL` — Base API path used by the frontend (e.g., `/api`).

---

## How to Run

For the Ubuntu sensor VM, copy `sensor_agent/` into Ubuntu 24.04 and run
`sudo bash setup_vm.sh --management-ip YOUR_HOST_ONLY_IP` from that directory.
This single script combines gateway networking, Zeek installation, Zeek/capture
autostart and sensor/Python setup. VirtualBox adapters and the Windows client are
prerequisites; see the [VM setup guide](sensor_agent/README.md) for the full command,
credentials, supported reruns and verification steps.

### 1. Start the Backend API

First reproduce or transfer the selected artifact using [the AI setup guide](ai/README.md).
The selected artifact is Git-ignored. Startup fails explicitly if an enabled model
is missing, incompatible or has a wrong checksum; it never silently bypasses inference.

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

The web application checks the HttpOnly session cookie on startup and restores
a valid administrator session automatically. Dashboard and connection data load
when entering their pages. There is no periodic polling. Filters, pagination, details and
completed commands load their related data following the user's action. Opening
or leaving a page idle does not fetch or analyze sensor logs. Zeek capture and
systemd service startup on Ubuntu are independent of these web controls.

1. Sign in at `http://localhost:5173/login` using the administrator credentials configured in `.env`. The login form does not prefill credentials.
2. On the **Live Dashboard** (`/dashboard`):
   - Click **Fetch & Analyze Logs** to pull the latest Zeek connection flows from the sensor, create a session, import and normalize new records, run the selected classifier, and display source connections and review findings. No analysis starts automatically.
   - Filter security alerts by severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and mark investigated alerts as resolved.
   - Use **Reset sensor cursor** to restart reading existing sensor logs (the log file is not deleted) or **Reset DB** to clear stored connections, alerts and analysis history. Sensor cursors are retained until separately reset.
3. Navigate to **Zeek Flows** (`/connections`) to inspect stored connection metadata, connection states (`SF`, `S0`, `REJ`), durations and directional byte/packet counts, filtered by protocol (`TCP`, `UDP`, `ICMP`).
   Select individual records or the current page, then choose **Analyze selection**
   to run the current model on existing connections. Reanalysis creates a new
   session and findings; unique connection totals do not grow simply because a
   connection was analyzed again.
4. In the dashboard's **Findings and review** feed, open **Details** for source
   evidence and use **Status** to record your review. Manually marked false-positive
   counts are feedback, not a measured false-positive rate or automatic retraining.
   CSV/JSON exports follow the selected severity and finding origin.

## AI training and inference

- Offline experiments in `ai/` train and compare Logistic Regression, Random Forest and Isolation Forest separately on TON_IoT Network and a published five-day Zeek re-extraction of CIC-IDS2017. The two datasets are not combined in the selected model.
- The current deployment selects `cic-endpoint_pairs-42` / `random_forest`, configured in `api/app/ai/deployment.json`. Its artifact is `api/app/ai/models/selected.joblib`.
- Inference uses five numerical fields (`duration`, `orig_bytes`, `resp_bytes`, `orig_pkts`, `resp_pkts`) and three categorical fields (`proto`, `service`, `conn_state`). Numerical transformations and missing-value indicators are shared with training. IPs, ports, UID and absolute timestamps are not classifier inputs.
- Findings are binary screening results labelled **Suspicious Connection**, with medium severity and source-record evidence. They do not identify a specific attack family. The stored `confidence` is an uncalibrated classifier score, not a verified attack probability.
- Isolation Forest remains an offline anomaly experiment. Processing new traffic does not retrain the selected model; retraining and model selection are explicit offline operations.
- [Measured results and confusion matrices](ai/reports/experiment_report.md), [machine-readable metrics](ai/reports/metrics.csv) and [reproduction, selection and transfer commands](ai/README.md) document the experiments and their limitations. Dataset results do not establish the alarm rate on a new network or performance on another computer.
- Downloaded datasets, prepared tables and run artifacts are under the Git-ignored `.ai-workspace/` directory. Trained `.joblib` files are also ignored. `python -m ai.export`, run from the repository root in the prepared environment, packages the selected model and manifest for transfer without raw traffic or credentials.

## Platform boundaries

- All alert, connection and system endpoints require an active administrator session. Login returns user and session metadata; the JWT is transmitted only in an HttpOnly cookie.
- Set secure-cookie options appropriately for deployment over HTTPS. Local HTTP development must use an explicit compatible configuration.
- The dashboard supports paginated alerts and connections, visible request errors, and Romanian/English themes and labels. Alert exports include all records matching the selected severity, not just the visible page.
- `api/app/ai/engine.py` defines the detector contract. Startup loads the explicit `api/app/ai/deployment.json` configuration. The initial classifier is a CIC Zeek Random Forest baseline; its dataset scores do not establish local-network performance. Isolation Forest remains an offline experiment and is not enabled. The transport and frontend do not depend on a specific model.
- The VM collector discovers current JSON conn.log streams and retained gzip archives. The backend commits each file cursor together with connections and alerts in SQLite, resumes across rotation, and analyzes only new connection UIDs. Retain unread archives until ingestion. Deploy the updated backend and sensor together. See [sensor setup and recovery](sensor_agent/README.md).
- Corrupt or individually unreadable sensor files are skipped for the current run
  and reported by filename/reason in analysis history. Other files continue;
  successful earlier batches remain stored and failed-batch cursors do not advance.
  Skipped files are retried on the next manual fetch. Backend startup applies an
  additive migration for persisted session `file_issues`; update the sensor too.
- Sensor mode describes configuration, not a live VM connectivity probe.
- Collection currently supports JSON `conn.log` records and retained connection-log archives. DNS, HTTP, TLS and host security-event log ingestion, behavioral time windows and automatic traffic blocking are not implemented. Connection-state badges are protocol metadata, not attack verdicts.
- Source files under `app/src/lib/` must be included when committing the frontend. Python environment directories remain ignored.

## Verification

### Pull request checks

For local secret detection before a commit, install the versioned Git hook once
per checkout (Windows/Linux x86_64, Python 3.10+ and Git):

```bash
python scripts/install_git_hooks.py
```

The installer downloads checksum-pinned Gitleaks into Git's private metadata
directory and sets this checkout's `core.hooksPath` to `.githooks`. It refuses to
replace another hooks configuration. The pre-commit hook scans staged additions,
including partially staged files, redacts detected values and blocks a commit if
it finds a potential secret or the scanner fails/is missing. It does not stage,
commit, push, alter files or restrict the branch name. Existing Git history is
scanned separately by the pull-request workflow. Do not treat a clean scan as a
guarantee that every possible secret format is detectable.

Git hooks are local controls and can be bypassed by a user with control of the
checkout (for example with `--no-verify`); they are not a server-side security
boundary. This hook applies to Git CLI commits from a person or an assistant.
Git GUI clients must support Git hooks; validate the specific client before
relying on it. A fresh clone requires running the installer again. To disable
this checkout's hook configuration intentionally, use
`git config --local --unset core.hooksPath`.

GitHub Actions runs only for pull requests targeting `main`, including updates
to those requests. There are no push, scheduled or deployment triggers.
`.github/workflows/ci.yml` runs the isolated backend unit suite (Python 3.13) and
frontend lint/build (Node 22, `npm ci`, explicit `VITE_API_BASE_URL=/api`).
`.github/workflows/security.yml` scans reachable Git history with Gitleaks and
audits frontend dependencies with `npm audit` (high/critical failures) and the
backend, sensor and offline AI requirements with `pip-audit` (all known findings).
Resolution errors also fail the audit; scanners never automatically update packages.

Actions are pinned to commit SHAs, checkout credentials are not persisted, and
the workflow token has read-only contents access. No application secrets, VM access,
datasets or selected model artifacts are required. `.gitleaksignore` documents one
exact historical documentation example; it does not exclude files or future secrets.
Making these checks mandatory before merge requires a GitHub branch protection
rule or ruleset configured separately.

### Ubuntu setup skill

The reusable `setup` skill is versioned in `.agents/skills/setup/`. Invoke it with
`$setup` and identify the Ubuntu VM to configure. It inspects the actual adapters
and existing credentials, transfers and runs `sensor_agent/setup_vm.sh`, diagnoses
scoped setup failures and reports repairs, verification and unresolved items.
The skill configures the gateway, Zeek and Python collector; the main API, database
and AI inference remain on the host. Loading the skill does not itself run setup.
Reboots and changes to the host/Windows client's networking require their own scope.

### Authentication and unit tests

Logout persists an individual JWT fingerprint and expiration in `revoked_tokens`.
Every protected request checks that table; a copied logged-out token remains
rejected after API restart. New tokens have unique IDs, and older unexpired
tokens can also be revoked. Expired revocations are pruned on subsequent logout.
Revocation storage failures fail logout rather than reporting success. Restart
the backend after updating so its normal startup applies the additive migration.
Clearing connection/alert history does not clear token revocations.

Backend unit tests live in `api/tests/unit/`. From `api/`, with the backend virtual
environment activated, run:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m pytest --cov=app --cov-branch --cov-report=term-missing
```

The suite checks authentication and cookie contracts, route authentication
dependencies, Zeek validation, feature preparation, classifier artifact/score
validation, sensor response contracts, UID deduplication, cursor conflicts,
analysis transaction ordering and failure/cancellation handling, reset/clear
guards, database-session cleanup and exports. Configuration, repositories and
HTTP boundaries use isolated test dependencies: no real `.env`, SQL connection,
VM, dataset or trained artifact is required. Unexpected SQL connections and
default HTTP transports fail the test. Unit assertions about commits and
rollbacks verify orchestration; they do not prove database durability, live
capture quality or classifier detection quality. Production startup/configuration,
database queries/migrations, actual HTTP routing and the complete VM flow still
require separate integration checks. Coverage includes unexecuted namespace
packages and is not an acceptance threshold. Test tooling is development-only.

Run `npm run build` and `npm run lint` from `app/`. Validate login/logout, expired
sessions, protected API requests, pagination, error recovery, exports,
theme/language persistence and mobile navigation manually. No frontend automated
test suite is included.

The recorded AI integration check used 200 real held-out records and a separate
SQLite database to verify offline/stored feature parity, API analysis and finding
evidence. See [the verification record](ai/reports/manual_verification.json).
Controlled VM traffic and additional CIC-source comparisons are documented in
[the follow-up report](ai/reports/live_cic_report.md). The selected model remains
unchanged: the measured scan detection does not establish reliable DoS/DDoS detection.
The Zeek autostart setup now prepares and verifies capture offloads on `enp0s8`
before every start, including boot; routing and NAT are unaffected.

## Analysis architecture and API

The manual sensor path is routes -> AnalysisService -> IngestionService -> normalization
and typed preparation -> shared feature extraction -> selected classifier -> findings
and repositories. Stored-record analysis reuses selected database records. The sensor
transport, authentication, archive discovery, UID deduplication and per-batch cursor
commits retain their existing behavior. No background ingestion or inference runs.

- `POST /api/system/fetch-and-analyze` remains the dashboard command. Its existing
  summary fields are retained and `analysis_session` is added.
- `GET /api/system/overview` returns persisted connection/session aggregates and
  requires the administrator cookie. Sensor access is exercised by an explicit
  fetch-and-analyze operation; there is no separate availability-probe endpoint
  in the main API. The collector's authenticated `/health` remains available for
  installer/service verification.
- Alert list, statistics and exports accept `provenance=analysis` or
  `provenance=legacy_demo`. The dashboard requests analysis-only statistics and
  lets users inspect demo history separately.
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
not a security verdict. For each batch, connections, source links, findings,
counts and cursor advancement commit together. A malformed record or failed detector
rolls back that batch and marks the session failed; earlier committed batches survive.
Detectors must return typed findings referencing only their batch's connection
IDs. The selected binary classifier uses shared core Zeek connection features;
its findings do not identify attack families. Behavioral time windows remain
unimplemented. The existing transport batch size is not a chosen analysis window.

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

- `api/app/ai/engine.py`: replaceable detector boundary; `detector.py` now loads only a locally selected, hash-verified classifier. `features.py` is shared by offline fitting and inference; `deployment.json` controls startup explicitly.
- `api/app/main.py`, `api/app/database/seed.py`, `api/migrations/env.py`, `api/app/models/__init__.py`: startup, migration registration and interruption recovery.
- `api/app/models/alert.py`, `api/app/repositories/alert_repository.py`, `api/app/repositories/connection_repository.py`: provenance, evidence and transactional resets.
- `api/app/schemas/alert.py`, `api/app/schemas/connection.py`, `api/app/schemas/system.py`: validation and compatible response extensions.
- `api/app/routes/system_routes.py`, `api/app/services/system_service.py`, `api/app/services/alert_service.py`: existing command compatibility, reset safety and export provenance.
- `app/src/components/dashboard/commands.tsx`, `app/src/components/dashboard/alerts.tsx`, `app/src/pages/dashboard.tsx`: manual commands, historical-demo labels and session integration.
- `app/src/services/api.ts`, `app/src/services/types.ts`, `app/src/i18n.tsx`: typed API integration and RO/EN text.
- `api/requirements.txt`: pinned CPU inference dependencies matching the recorded training environment. Offline-only data dependencies are in `ai/requirements.txt`.
- `README.md`: current architecture, lifecycle, API and file map.
