# Rotation and ingestion progress

## Blocked archive versions (2026-11-14)

User decision: report a permanent invalid/oversized archived-file error in its
first detecting analysis, then set that unchanged version aside. Keep a paginated
problem history with Retry. Current files and temporary access errors still retry.

Collector 2.6 adds authenticated POST /files/discover with excluded_versions.
Version fingerprints hash the relative path and stat device/inode/size/mtime_ns/
ctime_ns, not the full content. Blocked archived versions are skipped before any
content read; metadata changes permit another attempt. GET /files is retained for
diagnostics. Missing fingerprints are contract failures, not legacy fallbacks.

sensor_file_problems is separate from successful sensor_cursors. The first failure
and its session warning commit together. Blocked files are never marked completed.
Explicit retries/changed archives replay from zero using the saved checkpoint as
the compare-and-swap expectation; UID/event deduplication prevents duplicate data
and reclassification. Successful full reads resolve the problem. Empty repaired
archives are explicit in discovery and resolve problems without invented progress.
Historical session warnings remain unchanged. Full reset clears this history too.

/import-problems is linked from Settings and analysis-session cards. Authenticated,
sensor-scoped Retry queues a known problem under the analysis/reset write guard;
the UI then starts the normal coordinated analysis. Failed explicit attempts update
the same version row and are skipped on subsequent automatic runs again.

Verification: 388 isolated backend checks plus frontend build/lint passed. Live API
checks found the existing two NUL-tail archives as two blocked history rows. Two
consecutive analyses produced no warnings. Explicit retry incremented one row from
1 to 2 attempts, preserved first detection and reported just that file; the next
analysis had no warnings. Original archives were not modified. Collector deployed
to the existing /home/ubuntu/Desktop/nids_agent/sensor_agent.py with verified source
SHA-256 and backup /var/backups/nids-import-update.vhTY1Ail. Only the collector
service restarted; capture/network/credentials/AI settings were unchanged.


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

Read-only investigation, 2026-11-14: conn and dns archives for the
11:05:59-15:30:41 UTC interval were valid gzip streams but had NUL-filled tails
inside their decompressed content. Conn had one valid 333-byte JSON line followed
by 332 NUL bytes; DNS had one valid 361-byte line followed by 360 NUL bytes.
The collector correctly returned corrupt_file both from offset zero and the
saved offsets (333/361). Those offsets mark the next attempted read, not a
classifier result. The connection was UDP destination port 5353, not the test
broadcast on 49999. No raw records were stored in this note or changed on the VM.
The VM login history marks that prior session as crashed, and Zeek startup at
15:30 reported recovery/crash reporting for its previous node. This supports an
unclean VM/capture termination as the probable context; it does not establish
the exact write or filesystem event that produced the NUL padding. Do not silently
skip padding or claim that gzip decompression itself failed in this case.

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


Traffic table context (2026-11-14): ConnectionResponse now derives optional
server_name from the latest nonempty TLS server_name for the same UID, with
batched queries. Session connection responses use the same enrichment as the
traffic browser (previously they exposed only the default conn availability).
Shared traffic columns and session rows display SNI; missing names stay absent,
without DNS/IP guessing. Snapshot capture stores the name; older version-1
snapshots derive it only from their frozen TLS events, never live events.
Verification: 26 focused isolated backend checks, frontend build/lint and read-only
live API checks confirmed hvh.gg in both traffic and its session response.
