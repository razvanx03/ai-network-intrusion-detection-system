# Zeek sensor agent

The backend pulls connection logs on demand. `collector.py` is the authenticated,
read-only HTTP reader running on Ubuntu; the main API, database and AI inference
remain on the Windows host. Ingestion progress belongs to backend SQLite.

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

Copy this directory to Ubuntu. The setup needs `setup_vm.sh`, `collector.py` and
`requirements.txt` together. From the **VM console**, run:

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

If `/opt/nids-sensor/.env` already exists, it is reused. Otherwise, a real `.env`
beside the copied setup is used; if neither exists, setup generates a random API
key. The key is never printed and the installed `.env` is owned by the service
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
HTTP does not encrypt the key or logs; use the trusted isolated management network,
or arrange HTTPS before exposing this link to an untrusted network.

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
sudo systemctl status zeek nids-sensor --no-pager
sudo /opt/zeek/bin/zeekctl status
sudo ethtool -k enp0s8
sysctl net.ipv4.ip_forward
sudo iptables -t nat -S POSTROUTING
```

`zeek.service` remains a oneshot startup/shutdown unit; `active (exited)` alone does
not prove that Zeek is still capturing or recover it after a later crash. The sensor
uses restart-on-failure, which does not detect a hung process. Test actual client
traffic and pull logs from the backend after installing. Current JSON `conn.log`
and retained `conn.*.log[.gz]` archives are supported; other log types and TSV are not.

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
  The response also contains `issues` for files that cannot be discovered safely.
  Each issue supplies a relative filename and a stable code, without raw log data.
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
- Incomplete current-file lines remain unread. A sealed archive may end with valid
  JSON without a newline; genuinely truncated JSON is rejected. Malformed records,
  damaged gzip streams, oversized records and per-file access failures are reported
  explicitly. Updated `/logs` responses use HTTP 422 with a typed per-file code.
  The backend stops reading that file for this run and continues the other files,
  recording `file_issues` in the analysis session. No cursor is advanced over the
  failed batch; prior committed batches remain stored. A skipped file is retried
  from its retained cursor on the next manual fetch. No original log is changed
  or deleted. Connection/authentication failures and invalid transport contracts
  still fail the operation rather than masquerading as an empty sensor.
- The backend reset-cursor operation clears that sensor's SQLite progress without
  modifying VM logs. Re-reading retained logs deduplicates existing connection UIDs.
  Clearing connections/alerts alone leaves cursors intact; reset cursors too to re-import.
- There is no agent `/logs/ack` or `DELETE /logs` endpoint in this protocol.
- Retain archives longer than the maximum interval between successful pulls. Deleted
  unread files cannot be recovered. Do not edit historical files or use copy-truncate
  rotation. Gzip seeks require decompression and get slower with large archives.

Verify actual client traffic, current-log ingestion, archived-log ingestion, rotation
with an unread tail, and a repeat pull. Health proves HTTP availability, not capture.
