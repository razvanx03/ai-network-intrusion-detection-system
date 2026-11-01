# Zeek sensor agent

The backend pulls connection logs on demand. The agent is a read-only HTTP reader;
file progress lives in the backend's SQLite database, alongside connections and alerts.
Deploy the backend and agent together: version 2.2 replaces the previous batch/ack protocol.

## Installation

On Ubuntu 22.04/24.04 run `bash install_zeek.sh enp0s8`, using the interface that sees
the monitored traffic. The installer requires a standalone deployment and enables
JSON logging. The collector reads JSON `conn.log` and dated `conn.*.log[.gz]` archives;
other Zeek log types and TSV input are not supported.

Copy `.env.example` to `.env` beside `collector.py`. Configure all required settings:

- `AGENT_HOST`: preferably the Ubuntu host-only management IP, not the lab interface.
- `AGENT_PORT`: the HTTP listening port, normally `8000`.
- `API_KEY`: generate with `python3 -c "import secrets; print(secrets.token_hex(32))"`.
- `ZEEK_LOG_DIR`: `/opt/zeek/logs` for the standard `/opt/zeek` standalone layout.
  The active directory is `/opt/zeek/spool/zeek`; `logs/current` can be a symlink.
- `MAX_BATCH_RECORDS`, `MAX_BATCH_BYTES`, `MAX_LINE_BYTES`: bounded request budgets.
  Keep `MAX_BATCH_RECORDS=500` or greater for the backend's 500-record requests.

Protect `.env` with mode `0600`. Run the collector as an unprivileged account with
read/traverse access to active logs and newly rotated archives (for example,
membership in the Zeek log group). Do not run the collector as root. No agent state
file or writable state directory is needed.

Install dependencies in a virtual environment and start `.venv/bin/python collector.py`.
Alternatively use `.venv/bin/uvicorn collector:app --host MANAGEMENT_IP --port 8000`;
uvicorn requires explicit host/port flags. A renamed script uses its own module name.

After preparing the agent, `.env` and `.venv`, copy `setup_sensor_autostart.sh` into
Ubuntu and run it there. For the existing VM, whose collector is named `sensor_agent.py`:

```bash
sudo bash setup_sensor_autostart.sh \
  --agent-dir /home/ubuntu/Desktop/nids_agent \
  --script sensor_agent.py --user ubuntu --host 192.168.56.101
```

If you copy this whole folder instead, the script defaults to its own directory and
the filename `collector.py`; supply `--host` and optionally `--user`. The IP must
already exist on Ubuntu. Protect `.env` with `chmod 600` and ensure the selected
user owns/can read it before running the helper. The `zeek` group must already exist
and have read/traverse access to the logs; the helper does not change log permissions.

The helper validates dependencies/configuration as the service user, verifies the
generated systemd unit, backs up a changed existing unit, enables/restarts the single
`nids-sensor.service`, and checks authenticated `/health`. Rerunning also reloads an
updated agent or `.env`. It installs no packages and changes neither networking nor
Zeek. A manually launched agent occupying the port must be stopped manually first.
On failure inspect `sudo journalctl -u nids-sensor.service -n 60 --no-pager`; a backup
path is printed if the previous unit was replaced. Restart-on-failure handles a failed
process, not a hung one. This collector service remains separate from root Zeek capture.

For Zeek itself on Ubuntu 24.04, after configuring standalone capture on `enp0s8`,
run `sudo bash setup_zeek_autostart.sh`. It creates/enables `zeek.service` through
ZeekControl, backs up an existing unit, and verifies the node process and service
cgroup. If Zeek already runs outside the service, stop it before rerunning.
The setup also installs `/usr/local/sbin/nids-zeek-capture`. `ExecStartPre` runs it
before every Zeek start, including boot: TX checksum offloading, TSO, GSO, GRO
and LRO are disabled on `enp0s8` and verified with `ethtool`. This prevents Zeek
from discarding outgoing packets with unfinished checksums or seeing coalesced
packets. Zeek checksum validation stays enabled. `install_zeek.sh` installs the
required `ethtool` package; an existing installation needs it available too.
When upgrading an older active unit, first run `sudo systemctl stop zeek.service`,
then rerun the setup. A healthy rerun with the same unit reapplies offload flags
without restarting Zeek. The interface device is an explicit startup dependency.
The helper does not reboot or change routing, NAT, addresses or Zeek policies. Its two
sequential stop commands stop capture, then wait for background archive helpers.
The oneshot unit manages boot/shutdown, not continuous crash recovery:
`active (exited)` alone is not proof that Zeek is capturing. Check
`sudo /opt/zeek/bin/zeekctl status` after reboot.

## Backend and network

Set the root project `.env` to `SENSOR_MOCK_MODE=False`,
`SENSOR_AGENT_URL=http://UBUNTU_MANAGEMENT_IP:8000`, and
`SENSOR_AGENT_API_KEY` equal to the agent's `API_KEY`. Restart the backend after
configuration changes. Run the backend from `api/` when using its default relative
SQLite URL. Startup creates the `sensor_cursors` table if missing.

The Windows client routes lab traffic through Ubuntu's internal interface. A separate
host-only interface lets the Windows host backend reach the agent without exposing
the management endpoint on the monitored network. Use a trusted private network or
HTTPS because HTTP sends the API key without transport encryption.

## Protocol and recovery

- Every agent endpoint requires `X-API-Key`, including `GET /health`.
- `GET /files` discovers current and retained archived connection streams, excluding
  summary logs. Entries contain `file`, `file_id`, `archived`, and `first_ts`.
- `file_id` is a digest of the first complete connection record. Rename and gzip
  compression preserve it, including when the active file becomes an archive.
- `GET /logs?file=...&file_id=...&offset=...&limit=500` returns `records`,
  `next_offset`, `has_more`, and identity metadata. Offsets count **uncompressed bytes**
  and must be line boundaries returned by the agent. A mismatched stream returns 409;
  refresh discovery and retry the analysis action after rotation finishes.
- The backend drains discovered files in bounded batches. Each batch commits its
  connections, generated alerts, and cursor in one transaction. A failed batch does
  not advance its cursor; previously committed batches remain available in SQLite.
- Completed archives are skipped. Active files retain their byte offset. A renamed
  active file resumes at that offset in its archive before being marked completed.
- Existing connection UIDs are deduplicated and only new UIDs are analyzed. Retry or
  backend/agent restart does not require replaying committed records. Concurrent pulls
  can encounter a database conflict; retry rather than clearing progress.
- Incomplete current-file lines remain unread. Malformed JSON, unreadable archives,
  incompatible protocols and HTTP failures produce errors instead of empty fallbacks.
- The backend reset-cursor operation clears that sensor's SQLite progress without
  modifying VM logs. Re-reading retained logs deduplicates existing connection UIDs.
  Clearing connections/alerts alone leaves cursors intact; reset cursors too to re-import.
- There is no agent `/logs/ack` or `DELETE /logs` endpoint in this protocol.
- Retain archives longer than the maximum interval between successful pulls. Deleted
  unread files cannot be recovered. Do not edit historical files or use copy-truncate
  rotation. Gzip seeks require decompression and get slower with large archives.

Verify actual client traffic, current-log ingestion, archived-log ingestion, rotation
with an unread tail, and a repeat pull. Health proves HTTP availability, not capture.
