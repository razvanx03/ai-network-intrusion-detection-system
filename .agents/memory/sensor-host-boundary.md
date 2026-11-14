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


## Planned sensor HTTPS (user decision, 2026-11-14)

User wants HTTPS for backend-on-host to Ubuntu sensor, deferred to a later task;
do not implement as a side effect of other improvements. Automate provisioning in
the maintained setup so a separate laptop installation with its own Ubuntu and
Windows VMs receives fresh installation-specific keys/certificates. Keep the API
key for client authorization; backend must verify the sensor certificate using
the local CA, without disabling verification. Private sensor/CA keys must not be
copied into the frontend or committed. Provision public CA trust to the backend,
cover the configured sensor IP/name, and document expiry/renewal. Browser/backend
localhost HTTP is outside this planned change; Zeek capture, log contents and AI
inference should remain unchanged. Certificate failure must visibly stop fetching,
while Zeek continues recording. Verify ingestion and reset operations after setup.

Read-only evidence at discussion time: configured sensor endpoint used HTTP on
192.168.56.101:8000 and X-API-Key. Host listeners were loopback-only (::1:5173,
127.0.0.1:8000); SQLite is local. Effective VM firewall rules were not audited.
This is a future implementation decision, not evidence that TLS is deployed.
