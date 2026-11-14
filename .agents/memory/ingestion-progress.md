# Rotation and ingestion progress

The backend owns durable per-stream cursors in SQLite. The collector reads current
JSON `conn.log`, `dns.log`, `http.log`, `ssl.log` and retained archives, including gzip streams.
Offsets are uncompressed byte boundaries, not compressed-file offsets or line counts.
Stream identity survives rename/compression so a partially read current stream can
resume in its archive.

Protocol context (added 2026-11-07) has independent cursors and content-hash
deduplication. It is stored by UID even when conn.log has not arrived, then joined
when traffic is displayed. Multiple events per UID are valid. Do not pass DNS,
HTTP or TLS events to the connection classifier or count them as new connections.
Only allowlisted metadata is retained, excluding explicit HTTP credentials/bodies.
Existing connections can be enriched from retained context archives without
resetting their cursors. Tests cover rotation, typed file failures, duplicate
replay, validation before progress, absent parent connections and classifier bypass.
Live verification on 2026-11-07 imported retained context from the existing Ubuntu
sensor and displayed DNS answers, TLS negotiation metadata and multiple HTTP
transactions for individual UIDs. This used existing captured traffic, not a new
controlled attack scenario. The collector was updated at the legacy service path;
Zeek capture/network configuration was not changed.

Commit imported connections, findings and cursor progress together. A failed batch
must not acknowledge unread data. Do not replace this protocol with an agent-side
acknowledgement or delete logs after a health probe. Existing UIDs are deduplicated.

Confirmed on 2026-11-06: an archived gzip file had a genuinely truncated final JSON
record. Per-file corruption/access/size issues are now explicitly reported and
persisted as session `file_issues`; ingestion continues with other files without
advancing the failed batch's cursor. This is an intentional, visible partial
result, not a silent empty-data fallback. Network/authentication or malformed
transport-contract failures must still fail the operation. A sealed valid JSON
record without a final newline is accepted; partial active-file lines remain unread.

User decision, 2026-11-07: replace destructive database clearing with reversible
archive batches and remove cursor reset entirely from the UI/API/client/repository.
That UI decision was superseded on 2026-11-14 by an explicitly confirmed full
data-and-VM reset; see [data-reset.md](data-reset.md). Archival itself still leaves
cursors and VM logs unchanged.
Cursors remain unchanged during archival and restoration. Archived connection UIDs
still participate in deduplication, but not in stored analysis or current views.
All data explicitly includes archived traffic, alerts and sessions, with whole-lot
restoration that preserves source links, protocol context and review statuses.
Live archive/restore verification preserved every traffic/alert/session/context row
and the exact cursor fingerprint. The verification lot was restored afterward.

Evidence: `sensor_agent/README.md` under Protocol and recovery, the collector and
backend ingestion/cursor implementation. Verify those contracts and isolated unit
tests when making changes; the note is not proof that a live pull succeeded.
