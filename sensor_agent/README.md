# NIDS Zeek Sensor Agent

A lightweight edge telemetry daemon designed to run on a network monitor machine or Virtual Machine (VM) running **Zeek**.

It inspects Zeek's active connection log (`conn.log`), tracks byte-level file read offsets to stream only newly recorded flows, and exposes a secure REST API consumed by the central **AI NIDS** intelligence engine.

---

## Architecture Overview

```text
[ Network Traffic / Attacks ]
              │
              ▼ (Packet Sniffing)
     ┌───────────────────┐
     │   Zeek Monitor    │
     │  (conn.log file)  │
     └─────────┬─────────┘
               │
               ▼ (Incremental Tail / Offset)
     ┌───────────────────┐
     │ Sensor Collector  │  (FastAPI daemon: port 8000)
     │  (collector.py)   │  Protected with X-API-Key
     └─────────┬─────────┘
               │
               ▼ HTTP GET /logs (Polled on-demand)
     ┌───────────────────┐
     │   AI NIDS Core    │  (Backend API on Host)
     │ + Dashboard UI    │  Hybrid AI (IsolationForest + Heuristics)
     └───────────────────┘
```

---

## Features

- **Incremental Log Streaming**: Maintains a persistent byte offset cursor (`/tmp/nids_sensor_agent_offset.dat`). Every poll returns only newly recorded connection flows since the previous fetch.
- **Dual Format Support**: Automatically parses both Zeek **JSON-lines** (`@load policy/tuning/json-logs.zeek`) and default Zeek **TSV** format with automatic header extraction.
- **Rotation Resilience**: Detects file truncation or Zeek daily log rotation and automatically resets the read cursor to `0`.
- **API Key Authentication**: All telemetry ingestion and reset endpoints are protected by `X-API-Key`.
- **Zero Overhead**: Single-file Python daemon with minimal memory and CPU footprint.

---

## Prerequisites (On the VM)

- **Linux** (Ubuntu 20.04 / 22.04 / 24.04 or Debian recommended)
- **Python 3.10+**
- **Zeek** installed and capturing traffic

---

## Quick One-Shot Setup on the VM

### 1. Copy Files to the VM

From your host terminal (PowerShell or Bash), copy the `sensor_agent` directory to your VM:

```bash
scp -r sensor_agent user@<VM_IP>:~/sensor_agent
```

Or clone the repository directly on the VM:

```bash
git clone <REPO_URL>
cd ai-network-intrusion-detection-system/sensor_agent
```

---

### 2. Run the One-Shot Installer

Run `install_zeek.sh` on the VM. It automatically:
- Installs Zeek and system dependencies
- Auto-detects your active network interface (`enp0s3`, `ens33`, `eth0`, etc.)
- Configures native JSON logging (`@load policy/tuning/json-logs.zeek`)
- Deploys and starts Zeek traffic sniffing
- Sets up the Python virtual environment (`.venv`) and installs `requirements.txt`
- Generates `.env` from `.env.example`

```bash
cd sensor_agent
chmod +x install_zeek.sh
./install_zeek.sh
```

---

### 3. Run the Sensor Collector

Start the collector:

```bash
./.venv/bin/python3 collector.py
```

Or run in background:

```bash
nohup ./.venv/bin/python3 collector.py > collector.log 2>&1 &
```

Or using `uvicorn`:

```bash
uvicorn collector:app --host 0.0.0.0 --port 8000
```

> **Run as a Background Service (systemd)**
> To keep the collector running persistently, create `/etc/systemd/system/nids-collector.service`:
> ```ini
> [Unit]
> Description=NIDS Zeek Sensor Collector
> After=network.target
> 
> [Service]
> User=root
> WorkingDirectory=/home/user/sensor_agent
> ExecStart=/home/user/sensor_agent/.venv/bin/python3 collector.py
> Restart=always
> 
> [Install]
> WantedBy=multi-user.target
> ```
> Enable and start:
> ```bash
> sudo systemctl daemon-reload
> sudo systemctl enable --now nids-collector
> ```

---

## API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Returns agent status, log file existence, size, and cursor position. |
| `GET` | `/logs` | `X-API-Key` | Reads and returns all new Zeek connection flows since last poll. |
| `DELETE` | `/logs` | `X-API-Key` | Resets the log read cursor to 0. |

### Testing with `curl`

Check health:
```bash
curl http://<VM_IP>:8000/health
```

Fetch newly recorded flows:
```bash
curl -H "X-API-Key: nids-sensor-agent-secret-key" http://<VM_IP>:8000/logs
```

---

## Connecting Central NIDS to the VM

On your host machine, edit `.env` in the root of the project:

```env
SENSOR_MOCK_MODE=False
SENSOR_AGENT_URL=http://<VM_IP>:8000
SENSOR_AGENT_API_KEY=nids-sensor-agent-secret-key
```

When you click **Fetch & Analyze Logs** in the web dashboard, the backend will now pull live connection flows directly from the VM's Zeek sensor, run them through the AI detection pipeline, and display real network alerts in real time.
