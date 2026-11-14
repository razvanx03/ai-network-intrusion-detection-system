# Zeek sensor agent

The host backend pulls connection and DNS/HTTP/TLS logs during an analysis.
`collector.py` is the API-key-authenticated HTTP reader running on Ubuntu; the
main API, SQLite database and AI inference remain on the host. Analyses can be
requested manually or automatically by the signed-in application's availability
cycle. The collector does not push logs, schedule AI analysis or train models.

Collector **2.6.0** discovers JSON `conn.log`, `dns.log`, `http.log`, `ssl.log` and
their retained archives. The backend uses versioned `POST /files/discover` and
byte-offset `GET /logs`; `GET /files` is retained for diagnostics. Upgrade collector
and backend together. Use the unified setup for a new VM, or the scoped updater
for an existing installation described under [Explicit full reset](#explicit-full-reset).
No Zeek policy change is needed when its standard DNS, HTTP and TLS JSON logs
are already enabled. Unavailable/deleted protocol logs cannot be reconstructed.

## One-command Ubuntu VM setup

`setup_vm.sh` replaces the former `gateway_setup.sh`, `install_zeek.sh`,
`setup_zeek_autostart.sh` and `setup_sensor_autostart.sh`. Their four responsibilities
are implemented in one self-contained Bash script, with an overview comment and
numbered sections. The old helpers have been removed to avoid conflicting setup paths.

Prepare these VM adapters in VirtualBox before running it:

| Adapter | Default Ubuntu interface | Role |
|---|---|---|
| NAT | `enp0s3` | Internet access and the only IPv4 default route |
| Internal Network, e.g. `IDS-LAN` | `enp0s8` | Client LAN and Zeek capture; gateway `192.168.50.1/24` |
| Host-only | `enp0s9` | Windows host to sensor management, e.g. `192.168.56.101` |

Use **Ubuntu 24.04**, an existing non-root account with sudo, working Internet
access and systemd. The host-only adapter must already have its management IPv4
address (DHCP or an existing static configuration). Check addresses with
`ip -br -4 address`. Interface names/IPs can differ on another VM; use the script's
options. The three adapters must be distinct and their subnets must not overlap.

Copy the complete directory to Ubuntu. Setup requires `setup_vm.sh`,
`collector.py`, `requirements.txt`, `reset_logs.py` and `nids-reset.service`
together. From the **VM console**, run:

```bash
cd ~/sensor_agent
sudo bash setup_vm.sh --management-ip 192.168.56.101
```

Replace the example IP with the actual host-only address. One invocation performs:

1. **Gateway:** makes the client-side gateway address persistent, enables IPv4
   forwarding, adds bounded client forwarding/NAT and management-port rules, and
   persists IPv4 firewall rules without flushing unrelated policies. Existing
   NetworkManager profiles are configured with `nmcli`; networkd-based setups use
   a dedicated netplan file. The existing renderer/desktop networking is retained.
2. **Zeek:** installs the official Zeek 9.0 packages if absent, prepares the local
   standalone `[zeek]` node, enables JSON logs and grants the unprivileged sensor
   access to current and rotated logs. `zeekctl install` prepares configuration;
   capture is started by systemd, not by an unmanaged `zeekctl deploy` process.
3. **Zeek autostart:** installs `zeek.service` and its capture helper, disables and
   verifies TX checksum offloading, TSO, GSO, GRO and LRO before every start, and
   verifies ZeekControl status, the real capture PID, interface and service cgroup.
   Checksum validation stays enabled.
4. **Sensor autostart:** deploys `collector.py` to `/opt/nids-sensor`, creates its
   Python virtual environment, installs dependencies, prepares the protected
   `.env`, enables/restarts `nids-sensor.service` and checks authenticated health.
   It also installs/enables `nids-reset.service` with a restricted root broker;
   installation never invokes a reset or grants the collector general sudo access.

No automatic reboot is issued. Existing managed services are stopped during
configuration and started again when their stages succeed. Repeated runs keep the
same API key and avoid duplicate firewall rules/processes. A changed source
collector or dependencies are installed on rerun. The setup does not train/deploy
an AI model, configure VirtualBox itself, or change the Windows client/host.

For a read-only system/configuration preflight:

```bash
sudo bash setup_vm.sh --management-ip 192.168.56.101 --check
sudo bash setup_vm.sh --help
```

`--check` does not install packages, apply networking or change services. It is not
a full fresh-install test: package downloads, dependency installation and final
service checks happen only during actual setup. A complete installation must still
be validated on the newly created VM.

### Credentials and existing installations

An explicit `--env-file` takes precedence. Otherwise, `/opt/nids-sensor/.env`
is reused if present, then a real `.env` beside the copied setup. If none exists,
setup generates a random API key. The key is never printed and the installed `.env` is owned by the service
account with mode `0600`. Do not copy an unchanged `.env.example` to `.env`: its
placeholder key is intentionally rejected.

To migrate an older agent installation while preserving its key and limits:

```bash
sudo bash setup_vm.sh --management-ip 192.168.56.101 \
  --agent-user ubuntu --env-file /home/ubuntu/Desktop/nids_agent/.env
```

The selected CLI management IP and port configure the endpoint explicitly. Existing
configurations must supply every setting listed in `.env.example`; invalid/missing
settings are rejected instead of silently replacing the key. Changing the log path
away from `/opt/zeek/logs` is outside this setup's supported layout.

Configure the Windows host backend separately:

```dotenv
SENSOR_MOCK_MODE=False
SENSOR_AGENT_URL=http://192.168.56.101:8000
SENSOR_AGENT_API_KEY=<same API_KEY as /opt/nids-sensor/.env>
```

Read/copy the key locally from the protected file; do not commit either `.env` or
paste the key into shared logs. Restart the backend after changing its configuration.
HTTP does not encrypt the key or logs. The current installer does not generate
TLS certificates or configure HTTPS; certificate/trust provisioning is planned
separately. Use the trusted isolated management network and restrict access;
configure verified HTTPS separately before using an untrusted network.

The Windows client VM must be attached to the same Internal Network and configured
with a client address (e.g. `192.168.50.2/24`), gateway `192.168.50.1`, and a reachable
DNS server. No DHCP/DNS server is installed by this setup. The host-only address
must remain stable across boots; preserve its DHCP assignment or set it statically.

### Supported reruns and failure handling

The installer is intended for a fresh VM or the simple existing standalone layout.
It refuses an active UFW/firewalld/nftables manager, custom systemd drop-ins, unmanaged Zeek
processes, other Zeek series, conflicting internal routes/addresses and complex
bridge/bond/VLAN configurations. It does not disable these safeguards or unrelated
firewalls automatically. Integrate such custom configurations explicitly first.

Backups are kept in a root-only `/var/backups/nids-vm-setup.*` directory; the path is
printed on completion or failure. They may include credentials and must remain
private. Package/network/service installation is not a single atomic transaction:
on failure, the stage is reported and completed changes remain for inspection and
rerun. Packages are not automatically purged and old logs are not deleted. Backups
are local recovery material, not a promise of automatic full rollback.

After setup and after a manual reboot:

```bash
sudo systemctl status zeek nids-sensor nids-reset --no-pager
sudo /opt/zeek/bin/zeekctl status
sudo ethtool -k enp0s8
sysctl net.ipv4.ip_forward
sudo iptables -t nat -S POSTROUTING
```

`zeek.service` remains a oneshot startup/shutdown unit; `active (exited)` alone does
not prove that Zeek is still capturing or recover it after a later crash. The sensor
uses restart-on-failure, which does not detect a hung process. Test actual client
traffic and pull logs from the backend after installing. Current JSON `conn.log`,
`dns.log`, `http.log`, `ssl.log` and their retained JSON/gzip archives are supported.
Other Zeek log types and TSV are not imported by this collector.

## Backend and network

Set the root project `.env` to `SENSOR_MOCK_MODE=False`,
`SENSOR_AGENT_URL=http://UBUNTU_MANAGEMENT_IP:8000`, and
`SENSOR_AGENT_API_KEY` equal to the agent's `API_KEY`. Restart the backend after
configuration changes. Run the backend from `api/` when using its default relative
SQLite URL. Startup creates the `sensor_cursors` table if missing.

The Windows client routes lab traffic through Ubuntu's internal interface. A separate
host-only interface lets the host backend reach the sensor through a separate
management address. Full setup binds the agent to that address; an older/manual
installation may bind differently. Binding and firewall rules must match the
intended access scope. HTTP sends the API key without transport encryption.

## Log locations and context

| Path in the standard installation | Contents |
|---|---|
| `/opt/zeek/spool/zeek/` | Current logs being written by Zeek |
| `/opt/zeek/logs/YYYY-MM-DD/` | Rotated logs, commonly gzip-compressed |
| `/opt/zeek/logs/current` | Link to the current spool directory, not a second copy |

The reader is restricted to connection, DNS, HTTP and TLS JSON logs. Zeek can also
produce operational/security logs such as `stderr.log`, `stats.log` and
`notice.log`; these are not imported or passed to the selected classifier.
`stderr.log` and service journals help diagnose capture/service errors.

The backend links context by Zeek UID. Its Server name (SNI) column comes from
`server_name` in `ssl.log`, not a reverse DNS guess. The AI classifier uses only
connection features; imported context is for inspection and does not decrypt
HTTPS content. A flow may be logged only after closure or an inactivity timeout.

## Protocol and recovery

- Agent data, status and reset endpoints require `X-API-Key`, including `GET /health`.
- `POST /files/discover` accepts `{"excluded_versions": []}` and returns current/
  retained connection, DNS, HTTP and TLS streams. Entries contain `file`, `file_id`,
  `archived`, `log_type`, `first_ts` and a version `fingerprint`. The response also
  includes `issues` for discovery failures and `empty_files` for healthy sealed
  empty streams. `GET /files` provides the legacy diagnostic listing, not the
  backend's versioned discovery contract.
- `file_id` is a digest of the first complete record (namespaced for protocol context). Rename and gzip
  compression preserve it, including when the active file becomes an archive.
- `GET /logs?file=...&file_id=...&offset=...&limit=500` returns `records`,
  `next_offset`, `has_more`, and identity metadata. Archived reads also send the
  discovery `fingerprint` to reject a changed version before reading. Offsets count **uncompressed bytes**
  and must be line boundaries returned by the agent. A mismatched stream returns 409;
  refresh discovery and retry the analysis action after rotation finishes.
- The backend drains discovered files in bounded batches. Each batch commits its
  connection/context data, source links, generated alerts, session counts and
  cursor progress in one transaction. A failed batch does
  not advance its cursor; previously committed batches remain available in SQLite.
- Completed archives are skipped. Active files retain their byte offset. A renamed
  active file resumes at that offset in its archive before being marked completed.
- Existing connection UIDs are deduplicated and only new UIDs are analyzed. Retry or
  backend/agent restart does not require replaying committed records. Concurrent pulls
  can encounter a database conflict; retry rather than clearing progress.
- Incomplete current-file lines remain unread. A sealed archive may end with valid
  JSON without a newline; genuinely truncated JSON is rejected. Malformed records,
  damaged gzip streams, oversized records and per-file access failures are reported
  explicitly. Updated `/logs` responses use HTTP 422 with a typed per-file code.
  The backend stops reading that file for this run and continues the other files,
  recording `file_issues` in the analysis session. No cursor is advanced over the
  failed batch; prior committed batches remain stored. Permanent invalid/oversized
  archive versions are reported once, then set aside in import problem history.
  Changed versions and explicit Retry allow another read; current files and
  temporary access failures remain retryable. A blocked/retried archive replays
  from zero with deduplication and compare-and-swap against its retained cursor.
  No original log is changed or deleted by normal ingestion. Connection/
  authentication failures and invalid transport contracts still fail the operation
  rather than masquerading as an empty sensor.
- Archiving/restoring backend data never resets SQLite cursors or changes VM logs.
  The separate, explicitly confirmed full reset clears both VM logs and backend data/cursors.
  Archived UIDs remain deduplicated; use All data to restore an archive batch.
- There is no agent `/logs/ack` or `DELETE /logs` endpoint in this protocol.
- Retain archives longer than the maximum interval between successful pulls. Deleted
  unread files cannot be recovered. Do not edit historical files or use copy-truncate
  rotation. Gzip seeks require decompression and get slower with large archives.

Verify actual client traffic, current-log ingestion, archived-log ingestion, rotation
with an unread tail, and a repeat pull. Health proves HTTP availability, not capture.

## Explicit full reset

Normal discovery/reads and archive/restore operations never delete VM logs.
The application's Settings menu has a separate permanent full reset requiring
typed RESET confirmation. It is not a troubleshooting action to run automatically.

For an existing installation, copy the updated sensor_agent directory to Ubuntu
and run `sudo bash sensor_agent/install_reset.sh`. It discovers the existing
non-root collector service/user, updates its active script (`collector.py` or the
legacy `sensor_agent.py` filename) and installs `nids-reset.service` with the
root-owned `reset_logs.py` broker. It preserves .env and gateway settings,
backs up replaced files under /var/backups, and does not invoke log cleanup.
The full setup_vm.sh installer includes the same service.

GET /reset/capabilities and POST /reset require the sensor API key. The POST
requires a 32-character lowercase hexadecimal operation_id and confirmation RESET.
The collector retains NoNewPrivileges and contacts only the restricted Unix socket
/run/nids-reset/control.sock. The broker verifies the peer UID, stops zeek.service,
refuses cleanup if Zeek/rotation processes remain, clears .log/.log.gz files in
/opt/zeek/logs and /opt/zeek/spool/zeek without following symlinks, and restarts Zeek.
Control/configuration files stay. Capture resumes immediately, so fresh traffic
can appear after reset. Root-only recovery receipts in /var/lib/nids-reset prevent
retries of a completed operation from deleting newer captures. Do not delete these
receipts to resolve an interrupted reset. Retry from the application instead.

The backend persists a reset guard before issuing cleanup and deletes its own
traffic/archive/context/session/cursor/import-problem data only after the VM
acknowledges completion.
A timeout is an uncertain outcome, not proof that the VM did nothing: the guard
remains and the same operation must be resumed. The local and remote systems do
not support atomic rollback of permanent deletion. Neither VM installation nor
a live destructive reset is performed by unit checks.

## Blocked archive history

Collector 2.6 and the matching backend support authenticated POST /files/discover
with an excluded_versions JSON list. Version tokens fingerprint relative path and
stat device/inode/size/mtime/ctime metadata. Matching archived versions are skipped
before content reads. Modified versions are eligible again. GET /files remains the
legacy diagnostic listing. Archived /logs reads accept a fingerprint guard against
changes since discovery; current streams remain appendable.

The first permanent invalid/oversized archive failure is recorded in that analysis
and a separate problem history. Later analyses skip the unchanged blocked archive.
Current files and temporary access errors remain retryable. Import problem history
in Settings and session cards is paginated and has Retry. Successful reads resolve
the problem; failed explicit retries update the same row. Existing records/events
are deduplicated on replay. The source archives are never modified. Metadata-only
changes can also trigger a retry. Deploy matching collector and backend versions;
there is no silent legacy-protocol fallback.
