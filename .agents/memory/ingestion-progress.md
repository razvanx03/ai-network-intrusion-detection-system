# Rotation and ingestion progress

The backend owns durable per-stream cursors in SQLite. The collector reads current
JSON `conn.log` and retained connection-log archives, including gzip streams.
Offsets are uncompressed byte boundaries, not compressed-file offsets or line counts.
Stream identity survives rename/compression so a partially read current stream can
resume in its archive.

Commit imported connections, findings and cursor progress together. A failed batch
must not acknowledge unread data. Do not replace this protocol with an agent-side
acknowledgement or delete logs after a health probe. Existing UIDs are deduplicated.

Resetting the sensor cursor does not delete VM logs. Clearing stored connections
alone does not reset ingestion progress. Do not use either operation as a routine
way to fix connectivity; they change application state and need task authorization.

Evidence: `sensor_agent/README.md` under Protocol and recovery, the collector and
backend ingestion/cursor implementation. Verify those contracts and isolated unit
tests when making changes; the note is not proof that a live pull succeeded.
