# AI Network Intrusion Detection System (NIDS)

AI NIDS collects Zeek connection metadata (`conn.log`) and associated DNS, HTTP and TLS context from a remote sensor when an administrator requests it. The selected Random Forest classifier analyzes connection features, trained on a published Zeek-derived CIC-IDS2017 dataset, and flags suspicious connections for review. A React dashboard displays traffic records, protocol details, findings and traceable analysis sessions. Traffic tables share their metadata columns; the dashboard adds review status and classifier score, plus the same multi-protocol selector to filter active findings. See [AI experiments, results and reproduction](ai/README.md).

---

## Features

- **Replaceable AI boundary**: Typed input/finding contracts, shared versioned Zeek features and a locally selected classifier. Offline training compares Logistic Regression, Random Forest and Isolation Forest on TON_IoT Network and a Zeek-derived CIC-IDS2017 release.
- **Traceable sessions**: Durable status, per-batch counts, normalized source references and finding evidence. Existing demonstration alerts are preserved and explicitly labelled as demo history.
- **Connection classification**: Uses duration, directional byte/packet counts, protocol, detected service and connection state. Shared preprocessing preserves missing values and applies the same feature transformations during training and inference.
- **Operations dashboard**: Refreshes stored metrics and analysis status, provides a manual fetch-and-analyze command, paginated connection records, alert exports and reversible archival. An explicit sample mode reads bundled demonstration records.
- **AI review workflow**: Shows stored and flagged connections, the last successful sync, protocol distribution and daily alert totals. Switch between week and month views to see daily totals, including zero-alert days, based on the traffic timestamp in the browser's timezone. Archived alerts are excluded. Open a finding to inspect its model score and source connection; mark it as new, under investigation, resolved or false positive. Select multiple findings with the row checkboxes to apply one status atomically; the header checkbox selects the current page. Historical demo records remain preserved in the all-data view and are excluded from AI dashboard statistics.
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
when entering their pages. While signed in, Ubuntu agent availability is checked
on entry, manually from the header and one minute after each completed cycle.
When available, the check is followed by log retrieval and AI analysis. Failed
availability checks and sample mode do not trigger automatic analysis. Manual and
automatic sensor runs share a coordinator; overlapping requests are coalesced and
the backend guards concurrent analyses. Completed or partially failed runs refresh
mounted data without blanking the current content. Other data is not independently
polled. Agent availability does not confirm Zeek capture health. Filters, pagination, details and
completed commands load their related data following the user's action. Opening
or leaving a page idle does not fetch or analyze sensor logs. Zeek capture and
systemd service startup on Ubuntu are independent of these web controls.

1. Sign in at `http://localhost:5173/login` using the administrator credentials configured in `.env`. The login form does not prefill credentials.
2. On the **Live Dashboard** (`/dashboard`):
   - **Fetch & Analyze Logs** manually runs the same pipeline as the automatic follow-up: read new Zeek records, import and normalize them, run the classifier and retain evidence. The last-successful-sync card reflects completed sensor runs for the active dataset, not a health probe.
   - Filter security alerts by severity (`CRITICAL`, `HIGH`, `MEDIUM`, `LOW`) and mark investigated alerts as resolved.
   - Use **Archive data** to move all active traffic records, alerts and analysis sessions into one preserved archive batch. The dashboard, current flows, statistics and exports exclude archived data. Archiving leaves sensor cursors unchanged.
3. Navigate to **Zeek Flows** (`/connections`) to inspect stored traffic records, connection states (`SF`, `S0`, `REJ`), durations and directional byte/packet counts, filtered by one or more protocols discovered from the stored records. Available-data badges summarize its context; use **Details** to open the UID and DNS, HTTP and TLS metadata in a modal. Multiple transactions are retained and paginated; absent imported context is explicitly labelled.
   - **Settings / Delete all data** is an irreversible full reset requiring typed `RESET` confirmation. It removes traffic, findings, sessions, archive snapshots and import cursors, plus current/retained Zeek logs on the VM. Users, authentication, application configuration and the AI model are preserved. It refuses concurrent analysis. VM failure never reports success or clears local data; an interrupted reset blocks analysis until resumed with the same operation ID. Install sensor support first using `sudo bash sensor_agent/install_reset.sh` inside Ubuntu with the updated sensor_agent directory. Installation does not delete logs or change gateway networking.

4. **All data** (`/all-data`) has Traffic records and Analysis sessions views. The Filters popover contains Alerts only and Hide current data switches. Alerts only filters traffic records with AI findings, or sessions that generated findings; protocol selection applies to traffic. Selecting All protocols clears individual choices, and choosing individual protocols clears All. Restore a complete archive batch to return its records to current pages without reimporting logs or rerunning AI. Protocol context, source links, UIDs and alert review statuses are preserved. New sensor data continues from the existing cursors; already archived UIDs remain deduplicated.
   **View batch** opens `/archive-batches/:id`: a read-only historical copy with paginated traffic, protocol/alert filters, saved DNS/HTTP/TLS details and alert review statuses, and sessions with their traffic. Each new archive atomically saves its own snapshot. Restoring, changing live data or archiving again never changes earlier copies. Older batches without snapshots explicitly show retained totals only; their current data is not presented as historical content.

Manual sensor ingestion also reads JSON `dns.log`, `http.log` and `ssl.log`,
including gzip archives. Context is joined by Zeek UID and can arrive before or
after its `conn.log` record. Separate stream cursors and content hashes prevent
replay duplicates. Previously imported traffic can gain context on the next pull
without resetting connection cursors or rerunning the classifier. Retained archives
must still exist for backfill. Only explicitly selected protocol metadata is stored;
HTTP credentials, authorization headers and bodies are excluded. URI/query metadata
can still be sensitive. TLS metadata does not decrypt HTTPS content. The selected
AI classifier continues to consume only its existing connection features.
4. In the dashboard's **Findings and review** feed, open **Details** for source
   evidence and use **Status** to record your review. Manually marked false-positive
   counts are feedback, not a measured false-positive rate or automatic retraining.
   CSV/JSON exports include all active AI findings. Finding details open in a reusable modal with a source-evidence table and no pagination controls.

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
- The dashboard supports paginated alerts and connections, visible request errors, and Romanian/English themes and labels. Alert exports include all active AI findings, not just the visible page.
- `api/app/ai/engine.py` defines the detector contract. Startup loads the explicit `api/app/ai/deployment.json` configuration. The initial classifier is a CIC Zeek Random Forest baseline; its dataset scores do not establish local-network performance. Isolation Forest remains an offline experiment and is not enabled. The transport and frontend do not depend on a specific model.
- The VM collector discovers current JSON conn.log streams and retained gzip archives. The backend commits each file cursor together with connections and alerts in SQLite, resumes across rotation, and analyzes only new connection UIDs. Retain unread archives until ingestion. Deploy the updated backend and sensor together. See [sensor setup and recovery](sensor_agent/README.md).
- Corrupt or individually unreadable sensor files are skipped for the current run
  and reported by filename/reason in analysis history. Other files continue;
  successful earlier batches remain stored and failed-batch cursors do not advance.
  Skipped files are retried on the next manual fetch. Backend startup applies an
  additive migration for persisted session `file_issues`; update the sensor too.
- Sensor mode describes configuration, not a live VM connectivity probe.
- Collection supports JSON `conn.log` and UID-linked `dns.log`, `http.log`, `ssl.log` context, including retained archives. Host security-event ingestion, behavioral time windows and automatic traffic blocking are not implemented. Connection-state badges are protocol metadata, not attack verdicts.
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
and repositories. There is no stored-record reanalysis command. The sensor
transport, authentication, archive discovery, UID deduplication and per-batch cursor
commits retain their existing behavior. The signed-in UI can invoke the same pipeline
automatically after its successful periodic availability probe; no separate server scheduler runs.

- `POST /api/system/fetch-and-analyze` remains the dashboard command. Its existing
  summary fields are retained and `analysis_session` is added.
- `POST /api/archives` archives all active data atomically, `GET /api/archives`
  lists batches and `POST /api/archives/{id}/restore` restores a lot. Both writes
  reject running analyses. Normal data queries default to active records;
  the authenticated All data page explicitly requests `include_archived=true`.
  New archives also persist versioned `archive_records` payloads inside the same transaction.
  Authenticated `GET /api/archives/{id}`, `/{id}/protocols`, `/{id}/connections`,
  `/{id}/sessions`, `/{id}/connections/{connection_id}/events` and
  `/{id}/connections/{connection_id}/alerts` read batch-local snapshots only.
  Snapshot pagination is bounded; traffic filters accept repeated `protocols`,
  `alerts_only` and an optional batch-local `session_id`. Legacy snapshot reads
  return `409 archive_snapshot_unavailable`; unknown batches/records return 404.
  The former `/system/clear-database` and `/system/reset-sensor` endpoints no longer exist.
- `GET /api/system/overview` returns persisted connection/session aggregates and
  requires the administrator cookie. Sensor access is exercised by an explicit
  fetch-and-analyze operation. `GET /api/system/sensor-status` probes only the
  collector's authenticated `/health`, with a bounded timeout and explicit
  unavailable, sensor-authentication and invalid-response states. When HTTP cannot
  connect, a bounded ICMP check distinguishes agent unavailability (Ubuntu responds),
  host/network unreachability, and unknown reachability. A firewall may block ICMP;
  missing replies do not prove the VM is powered off. `/health` also remains available for
  installer/service verification.
- Alert list, statistics and exports accept `provenance=analysis`.
  The dashboard always shows and exports AI findings. The all-data view filters traffic and analysis sessions by archived-only or alerts-only scope, and preserves
  access to historical records without a separate demo-history selector.
- `GET /api/analysis-sessions?limit=20&offset=0` lists history; `GET /{id}` retrieves
  status, counters, detector/preparation metadata and safe error codes.
- `GET /api/analysis-sessions/{id}/connections` and `/alerts` return paginated
  source records and findings. `/alerts/{alert_id}/connections` returns exact evidence,
  including multiple connections for a future aggregate finding.
- All endpoints require the existing admin cookie. Failures return a safe code and
  session ID; credentials and remote response bodies are never sent to the frontend.

Sessions are request-driven and use **one API worker**. A database constraint rejects
concurrent analysis; reset operations refuse while a session is running. Restarting
the API marks unfinished sessions interrupted. The next automatic or manual run resumes: committed batches
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
