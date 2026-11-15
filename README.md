# AI Network Intrusion Detection System (AI NIDS)

AI NIDS captures network traffic with Zeek on an Ubuntu gateway VM, imports
connection records and DNS/HTTP/TLS context into a backend on the host, and uses a
selected Random Forest classifier to flag suspicious connections for review.
The React application provides traffic browsing, analysis history, alert review,
exports and browsable archive snapshots.

A finding is a screening result, not confirmation of an attack. The classifier
score is not a calibrated attack probability. Processing traffic does not retrain
the model, and an absence of alerts is not proof of safety.

## Architecture

```text
Windows client VM -> Ubuntu gateway VM -> Internet
                     | Zeek capture on the client-LAN interface
                     | conn.log, dns.log, http.log, ssl.log
                     v
Host backend <--- authenticated HTTPS log reads over host-only management network
  | SQLite: traffic, context, findings, sessions, cursors and archive snapshots
  | AI inference: newly imported connection UIDs only
  v
Browser -> localhost:5173 -> /api proxy -> localhost:8000
```

The host running the backend can be a desktop or laptop. The monitored Windows
client is a separate VM; its traffic must pass through Ubuntu. A client adapter
that reaches the Internet directly can bypass capture. VirtualBox adapter setup
and client IP/gateway/DNS settings are configured separately from the application.

| Directory | Purpose |
|---|---|
| `api/` | FastAPI, SQLAlchemy, SQLite, authentication, ingestion and AI inference |
| `app/` | React, TypeScript, Vite, Tailwind CSS, shadcn/ui and file-based routes |
| `sensor_agent/` | Ubuntu gateway/Zeek setup, authenticated collector and reset broker |
| `ai/` | Offline acquisition, preparation, model comparison, export and measured reports |
| `.agents/` | Project notes and the reusable Ubuntu setup skill |

See the [sensor setup guide](sensor_agent/README.md) and
[AI reproduction and results guide](ai/README.md) for their detailed workflows.

## Requirements

- Python 3.13 for the pinned backend/AI environment.
- Node.js 20.19+ in the 20.x line, or 22.12+, and npm.
- Ubuntu 24.04 with systemd for the sensor VM, three configured network adapters
  and an existing non-root account with sudo.
- The versioned selected AI artifact matching `api/app/ai/deployment.json`;
  databases, credentials, downloaded datasets and experimental artifacts stay local.

The application currently uses SQLite-specific ingestion and query behavior.
Changing `DATABASE_URL` to a different database engine alone is not a supported
migration path.

## Setup and run

### 1. Configure the Ubuntu sensor

Copy the complete `sensor_agent/` directory into Ubuntu. From its VM console:

```bash
cd ~/sensor_agent
sudo bash setup_vm.sh --management-ip 192.168.56.101
```

Use the actual host-only IP of that installation. The script configures gateway
routing/NAT, standalone Zeek JSON capture, offload preparation, log permissions,
the Python collector and the restricted reset service. It does not configure
VirtualBox, the Windows client, the host backend or an AI model. It does not reboot
or delete existing logs. Read the [sensor guide](sensor_agent/README.md) for
prerequisites, `--check`, supported reruns, credentials and verification.

### 2. Configure the host application

Copy `.env.example` to `.env` in the repository root:

```powershell
Copy-Item .env.example .env
```

Review every setting before starting:

| Setting | Meaning |
|---|---|
| `SECRET_KEY` | JWT signing secret; use a generated secret for a real deployment |
| `ADMIN_USERNAME`, `ADMIN_PASSWORD` | Initial admin seed credentials |
| `DATABASE_URL` | SQLite URL; the example resolves to `api/data/nids.db` when run from `api/` |
| `CORS_ORIGINS` | Explicit browser origins allowed to use the cookie-authenticated API |
| `COOKIE_SECURE`, `COOKIE_SAMESITE` | Cookie settings appropriate to local HTTP or deployed HTTPS |
| `SENSOR_MOCK_MODE` | `True`: explicit bundled sample mode; `False`: real Ubuntu sensor |
| `SENSOR_AGENT_URL` | Verified HTTPS sensor origin, e.g. `https://192.168.56.101:8000` |
| `SENSOR_CA_CERT` | Public installation CA file; relative paths resolve from the repository root, required for remote mode |
| `SENSOR_AGENT_API_KEY` | The same secret as the sensor's protected `API_KEY` |
| `VITE_API_BASE_URL` | Frontend API base; `/api` uses Vite's local backend proxy |

The frontend also reads the root `.env`; a separate `app/.env` is not required.
The root `.env` is required by the backend. Required configuration errors stop
startup; remote sensor failures never silently switch to sample data.
Example credentials are public examples, not deployment secrets. Seeding creates
an admin only if that username is absent; changing `.env` does not reset an
existing account's password.

### 3. Prepare the host environment and selected model

From the repository root:

```powershell
python -m venv api/.venv
& api/.venv/Scripts/python.exe -m pip install -r api/requirements.txt
```

The selected trained model, `api/app/ai/models/selected.joblib`, is included in
Git alongside its deployment manifest and pinned backend requirements. A fresh
clone already contains the artifact; no separate model transfer or training is
needed. Install the pinned requirements before starting the API. To intentionally
replace the model, follow the [AI guide](ai/README.md).

`api/app/ai/deployment.json` currently enables `cic-endpoint_pairs-42` /
`random_forest`. An enabled model with a missing artifact, wrong SHA256, incompatible
feature schema or mismatched dependency versions fails startup, including in
sample mode. Inference can be explicitly disabled with `enabled: false` in that
manifest; this produces no AI findings and is not a safety verdict.

### 4. Start the backend

In a terminal opened at the repository root:

```powershell
cd api
& ./.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Use one API worker. Startup loads the selected model, bootstraps/evolves the
schema, seeds the missing admin and marks unfinished analyses interrupted.
The API is at `http://localhost:8000/api`; interactive docs are at
`http://localhost:8000/docs`.

### 5. Start the frontend

In a second terminal at the repository root:

```powershell
cd app
npm ci
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to `http://localhost:8000`.
The application restores a valid HttpOnly cookie session or displays login.
Language and theme preferences persist locally; authentication does not use
localStorage.

## Using the application

### Collection and analysis lifecycle

Zeek captures independently of the web application. While the administrator is
signed in, the shared header checks agent availability on mount, on manual
refresh and one minute after the preceding check-and-analysis cycle completes.
A successful remote-agent check triggers log retrieval and analysis. The timer
stops on logout/unmount. Sample mode and unsuccessful checks do not automatically
analyze; the dashboard's manual command remains available.

Manual and automatic analysis use the same coordinator. Overlapping UI requests
are coalesced, and the backend rejects concurrent analyses. Successful and
partially failed runs refresh mounted data. Other page data is not independently
polled; filters, pagination and details load their own results on demand. There is
no server-side scheduled analysis or durable job queue.

If the sensor is unavailable, the backend can still serve previously stored data.
The host API and its database must remain available. Agent health proves HTTP
availability, not that Zeek is actually capturing packets.

### Pages and controls

- **Dashboard** (`/dashboard`): active traffic/session metrics, daily alert totals,
  analysis history, manual fetch, archival, CSV/JSON export and the suspicious
  connections table. Review findings as new, under investigation, resolved or
  false positive. Checkboxes support atomic bulk status changes for up to 500
  selected active AI findings. The protocol selector filters findings and their
  linked traffic; overview metrics retain their global scope. There is no
  severity filter; the selected detector currently produces medium-severity findings.
- **Zeek Flows** (`/connections`): current stored traffic with multi-protocol
  filtering, service, connection state, duration and directional bytes/packets.
  Details show the UID and paginated DNS/HTTP/TLS metadata. There is no selection
  or action to reanalyze already stored connections.
- **All data** (`/all-data`): archive batches above Traffic records and Analysis
  sessions views. Filters provide **Alerts only** and **Hide current data**;
  protocols apply to traffic only. Alerts only means traffic linked to AI findings,
  or sessions that generated findings. All protocols clears individual choices.
  Filter triggers visibly indicate non-default selections.
- **Archive batch** (`/archive-batches/:id`): read-only traffic, saved context,
  findings/statuses and sessions from that batch's immutable snapshot. Restore
  returns records to current views without rewriting the historical copy. Older
  batches without snapshots show totals and explicit snapshot unavailability.
- **Import problem history** (`/import-problems`): paginated permanent archive
  failures, first/latest detection, offset, attempts and blocked/retry/resolved/
  outdated status. Available from Settings and analysis-session cards.

Session details show imported connections and alert totals. They do not repeat a
second session-alert list. Alerts remain accessible through the shared traffic/
finding views. A session can import zero records, or import connections captured
before the session started: Zeek may write records after closure or timeout.

### Reading the traffic tables

Traffic browsers, archived traffic and dashboard findings share traffic columns;
findings additionally have classifier score, review status and selection/actions.
Session connection tables use a shorter UID/source/destination/server/protocol view.

| Field | Meaning |
|---|---|
| Available context badges | Imported `conn`, DNS, HTTP or TLS data for that UID |
| Protocol | Zeek's `proto`, e.g. TCP, UDP or ICMP |
| Service | Detected application service, e.g. `dns`, `http`, `ssl`, `quic,ssl` |
| Server name (SNI) | Latest nonempty `server_name` from `ssl.log` for that UID; `—` if absent |
| Connection state | Zeek state such as `SF`, `REJ`, `S0`, `RSTO`, `RSTR` or `OTH`; not an AI verdict |
| Bytes / packets | Originator / responder counts, not a fraction of a total |

SNI is context, not an AI input, and is not inferred from an IP or DNS query.
Encrypted HTTPS content is not decrypted. HTTP credentials, authorization fields
and bodies are excluded from imported context; permitted URLs and DNS queries
can still contain sensitive metadata.

### Archives, exports and full reset

**Archive data** moves active traffic, alerts and sessions into a reversible batch
and atomically captures its snapshot. Normal archival/restoration preserves UIDs,
review statuses, evidence and protocol context; it never clears sensor cursors or
VM logs. Already archived UIDs remain deduplicated. New archives have independent
historical copies even after restoration and rearchival.

**CSV/JSON exports include all active AI findings**, not just the visible page or
protocol selection. They do not export all raw traffic or archived findings.

**Settings / Delete all data** is a separate irreversible operation requiring the
literal confirmation `RESET`. It removes backend traffic, context, findings,
sessions, archives/snapshots, cursors and import problem history, plus current and
retained Zeek logs on Ubuntu. Users, token revocations, application configuration,
AI artifacts and reset recovery receipts are preserved. Capture restarts afterward,
so new traffic may appear immediately.

The reset requires compatible VM support, refuses concurrent analysis and blocks
analysis/archive/retry operations while pending. Local data is cleared only after
the VM acknowledges cleanup and capture restart. Remote deletion cannot be rolled
back; an uncertain outcome must be resumed with the same operation ID. See the
[sensor reset guide](sensor_agent/README.md#explicit-full-reset) for the scoped
updater and recovery behavior.

## Ingestion, failures and database evolution

The backend discovers current/archived JSON `conn.log`, `dns.log`, `http.log` and
`ssl.log` streams through collector 2.6's authenticated `POST /files/discover`.
It drains them in bounded batches with per-stream uncompressed-byte cursors.
Rename/gzip rotation preserves stream identity. Connection UIDs and protocol-event
hashes prevent replay duplicates. Context can arrive before or after its connection
and enrich existing records without rerunning the classifier.

Each successful batch commits data, evidence, counts and cursor progress together.
A failed batch does not advance its cursor; previous committed batches survive.
Completed archives are skipped. Partial current lines wait for a later read.

A permanent corrupt/oversized archived-file version is reported in the detecting
session and recorded separately in import problem history. Unchanged blocked
versions are omitted from subsequent reads; changed versions and explicit Retry
permit replay with deduplication. Successful complete reads resolve the issue;
failed retries update its existing history entry. Current files and temporary
access failures remain retryable. Transport/authentication failures or invalid
response contracts fail the analysis rather than returning fabricated empty data.
The application never repairs or edits the source log to suppress a warning.

SQLite tables cover users/revocations, connections/protocol events,
alerts/evidence, analysis sessions/source links, archive batches/snapshots,
sensor cursors, sensor file problems and reset receipts. Startup runs the
`create_all` bootstrap followed by Alembic **upgrade to head**, not a fixed old
revision. Migrations preserve existing data and label older demonstration alerts
`legacy_demo`; current AI dashboards/exports select `analysis` provenance.
Back up the database before an upgrade. Existing migrations do not reconstruct
missing historical snapshots or recover deleted source traffic.

## AI model and measured limits

The deployed classifier uses five numerical fields (`duration`, `orig_bytes`,
`resp_bytes`, `orig_pkts`, `resp_pkts`) and three categorical fields (`proto`,
`service`, `conn_state`). Numerical log transforms and missing indicators are
shared with offline training. IPs, ports, UID, absolute timestamps, DNS/HTTP/TLS
context and time-window counts are not inputs.

Each newly imported connection is screened separately. Repeated similar records
can receive the same score, and several alerts can arise from one scan. The model
does not aggregate a scan, count requests per second or identify an attack family.
Binary findings are labelled **Suspicious Connection**. Isolation Forest and
other candidate sources/features remain offline experiments unless explicitly
selected and integrated.

See [AI setup and selection](ai/README.md), the
[baseline report](ai/reports/experiment_report.md),
[live/CIC follow-up](ai/reports/live_cic_report.md) and
[source/feature extension](ai/reports/extension_report.md).
Reported dataset metrics and controlled VM results do not establish universal
accuracy, reliable DoS/DDoS detection or the alarm rate on another network.

## API reference

The default API prefix is `/api`. Data/system routes require an active admin
cookie. The sensor uses a separate API key, which never belongs in the frontend.

| Endpoint | Purpose |
|---|---|
| `POST /auth/login`, `POST /auth/logout`, `GET /auth/me` | Cookie session lifecycle |
| `GET /logs/connections`, `GET /logs/protocols` | Paginated traffic and available protocols |
| `GET /logs/connections/{id}/events` | UID-linked context, filtered by kind |
| `GET /alerts`, `/alerts/stats`, `/alerts/daily` | Findings and aggregates |
| `POST /system/fetch-and-analyze` | Import new records and run AI in a durable session |
| `GET /system/overview`, `/system/sensor-status`, `/system/health` | Stored overview and bounded availability/status checks |
| `GET /analysis-sessions`, `GET /analysis-sessions/{id}` | Session history and status |
| `GET /analysis-sessions/{id}/connections` | Paginated session source records |
| `GET /analysis-sessions/{id}/alerts/{alert_id}/connections` | Exact finding evidence |
| `POST /archives`, `GET /archives`, `POST /archives/{id}/restore` | Archive/restore complete batches |
| `GET /archives/{id}` | Batch metadata and retained totals |
| `GET /archives/{id}/protocols`, `GET /archives/{id}/connections`, `GET /archives/{id}/sessions` | Batch-scoped snapshot records |
| `GET /archives/{batch_id}/connections/{connection_id}/events`, `GET /archives/{batch_id}/connections/{connection_id}/alerts` | Snapshot context and findings |
| `GET /system/import-problems`, `POST /system/import-problems/{id}/retry` | Import history and explicit retry |
| `GET /system/reset-status`, `POST /system/reset-data` | Guarded permanent full reset |

See `/docs` for request schemas, status changes, export routes and pagination limits.
There is no stored-record reanalysis endpoint or separate session-alert list API.
Backend restarts mark unfinished analyses interrupted; later runs resume from
committed progress. A bounded ICMP fallback helps describe host reachability when
agent HTTP fails; missing responses do not prove the VM is powered off.

## Authentication and transport

Passwords are hashed with bcrypt; JWTs are held only in HttpOnly cookies.
Logout persists an individual token fingerprint and expiry in `revoked_tokens`,
so a copied logged-out token stays rejected after restart. New sessions have
unique token IDs. Failed revocation storage fails logout rather than claiming
success. Full data reset preserves authentication and revocations.

The sensor setup uses **HTTPS with `X-API-Key`**, bound by the installer to
the management address. HTTPS protects the API key, commands and returned logs. The installer generates
an installation-specific CA and server certificate (approximately ten years).
Copy only the public `tls/ca.crt` from the sensor to host `certs/sensor-ca.crt`;
set `SENSOR_CA_CERT=certs/sensor-ca.crt`. The backend rejects missing trust files,
HTTP remote URLs, expired/untrusted certificates and mismatched server addresses.
It does not install the CA into Windows/browser global trust. Keep the API key
for caller authorization. Browser-to-localhost development HTTP is unchanged.
See [sensor HTTPS setup and renewal](sensor_agent/README.md#https-certificates-and-laptop-installations).

## Development checks

From `api/`, with the backend virtual environment available:

```powershell
& ./.venv/Scripts/python.exe -m pip install -r requirements-dev.txt
& ./.venv/Scripts/python.exe -m pytest tests/unit -q
& ./.venv/Scripts/python.exe -m pytest tests/unit --cov=app --cov-branch --cov-report=term-missing
```

The isolated backend suite covers authentication, validation, AI contracts,
exports/status changes, archival, reset recovery, sensor contracts, ingestion
progress/failures and import problem history. It uses simulated boundaries and
synthetic temporary files: no real `.env`, application database, VM, dataset or
deployed model is loaded. Unexpected SQL connections and default HTTP transports
fail tests. Commit/rollback assertions check orchestration, not actual database
durability. Startup, migrations, live capture and detector accuracy require
separate verification. No frontend automated suite is included.

From `app/`, run `npm run build` and `npm run lint`. Manually verify login/logout,
error recovery, filter/pagination stability, details, exports, mobile navigation
and theme/language persistence when changing the UI.

Install the local staged-secret hook once per checkout:

```powershell
python scripts/install_git_hooks.py
```

It installs checksum-pinned Gitleaks under Git metadata and configures
`.githooks`. It scans the index, redacts findings and blocks on a secret or scanner
failure; it does not stage, commit or push. Hooks can be bypassed locally and do
not guarantee discovery of every secret. Example credentials remain public.

GitHub Actions run **only for pull requests targeting `main`**, not direct pushes,
schedules or deployments. CI runs backend unit tests and frontend build/lint;
security checks scan reachable history and audit frontend/backend/sensor/offline
AI dependencies. Actions are pinned, checkout credentials are not persisted and
the token has read-only contents permissions. Required checks/branch protection
must be configured separately.

The reusable Ubuntu `$setup` skill is versioned in `.agents/skills/setup/`.
It inspects and configures the sensor; loading it does not itself run installation.
