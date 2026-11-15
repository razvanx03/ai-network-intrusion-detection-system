# Sensor and host responsibilities

Confirmed architecture: Ubuntu is the monitored client gateway and runs Zeek plus
the Python collector (normal log reads are read-only; an explicitly authenticated
full-reset endpoint was added on 2026-11-14). The main FastAPI backend, SQLite ingestion progress
and AI inference run on the host. The backend pulls logs when the user requests
analysis; the collector does not push logs or retrain the model.

Use `sensor_agent/setup_vm.sh` for maintained VM installation. It combines gateway,
Zeek, capture/autostart and collector/autostart setup. The former individual setup
scripts have been removed from the repository; old VM desktop copies may remain.
Read the current installer before a rerun instead of treating those copies as current.

The collector service is `nids-sensor.service`. The unified installer deploys it to
`/opt/nids-sensor`; an older VM installation used a directory on the user's desktop.
Inspect the actual unit before assuming its executable or `.env` path.

Evidence: `sensor_agent/README.md`, `sensor_agent/setup_vm.sh`, `sensor_agent/collector.py`.
Service health establishes HTTP availability, not successful packet capture or
end-to-end ingestion. No VM or backend state is guaranteed by this note.


## Verified sensor HTTPS (2026-11-15)

User explicitly requested implementation and deployment on branch codex/sensor-https.
The maintained setup now provisions an installation CA and IP-SAN server certificate
(approximately ten years). Scoped install_https.sh MANAGEMENT_IP supports legacy
service paths without reconfiguring gateway/Zeek or deleting logs. --renew preserves
CA trust while renewing the server identity. Keep private keys on their installation;
copy only public tls/ca.crt through a trusted channel to host certs/sensor-ca.crt.
A laptop with new VMs generates its own material; source and model are transferable,
installation .env and keys are not Git content. CA expiration needs deliberate new
trust distribution. The backend requires an HTTPS origin and valid SENSOR_CA_CERT
in remote mode, resolves relative paths from repository root and uses verified TLS
with environment proxies disabled on every sensor call. API-key authorization remains.

Deployment evidence: existing Ubuntu service working directory was
/home/ubuntu/Desktop/nids_agent, script sensor_agent.py, management 192.168.56.101.
Verified authenticated HTTPS health/discovery, bounded current and healthy archive
reads, reset capability (not destructive reset), rejection of missing API key,
untrusted CA, wrong hostname and plaintext HTTP. Host API through Vite successfully
restored auth, queried data/sessions and ran AI ingestion over HTTPS. Repeat analysis
reported no import issues; retained corrupt archives were quarantined normally.
Capture remains bound to the client LAN. Two Windows client pings were captured
and imported over HTTPS (ICMP 2/2 packets); a HEAD example.com probe returned 200
and appeared in Zeek http.log. 450 isolated backend units and frontend build passed.
No reboot test or port-scan test was run;
user reserved the attack test for themselves. These are dated observations, not
ongoing guarantees of VM availability.

During deployment root pip inherited umask 077 and newly installed optional Python
packages were unreadable to the service account. Evidence was uvloop/websockets
import errors. Corrected package readability and installer dependency umask to 022;
normal service startup and verified HTTPS then passed. Bash copies require LF;
VirtualBox copyto uses absolute host source paths.

Configuration comment preference (2026-11-15): describe the setting neutrally;
do not put task-specific handoff instructions (such as "copied from this
installation") in .env examples. Keep reusable setup steps in documentation.
