# Sensor and host responsibilities

Confirmed architecture: Ubuntu is the monitored client gateway and runs Zeek plus
the read-only Python collector. The main FastAPI backend, SQLite ingestion progress
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
