# Archive history

User clarification, 2026-11-14: archive batches must remain browsable exactly as
they were when archived, including after restoration and later archiving. Exact
reconstruction of older batches is not required. Counts alone are insufficient.

Confirmed cause: restoration clears live archive_batch_id fields. They represent
current archival membership, not historical membership, so do not use them to
reconstruct restored batches. New archives capture version-1 archive_records in
the same locked transaction as membership updates. Snapshot failures roll back
the complete operation. Restoration never writes snapshots.

Payloads preserve traffic, alert scores/statuses, sessions, evidence/session links
and whitelisted protocol events. Referenced traffic outside the batch is copied
for session/evidence context with member=false, excluded from the batch traffic
total. No sensor URL or credentials are copied. Snapshot reads are authenticated,
paginated, batch-scoped and independent of live tables. The read-only browser is
/archive-batches/:id and reuses the shared traffic columns and details modal.

Legacy batches have snapshot_version=NULL and show totals with an explicit
unavailability message; never silently substitute current records. New context
events received after archiving belong to live data and later snapshots, not the
older copy. There is no per-snapshot rewrite or deletion endpoint. The separately
confirmed full data reset added on 2026-11-14 clears all snapshots too; see
[data-reset.md](data-reset.md).

Verification: isolated backend unit tests cover transaction rollback, detached
payloads, membership, context whitelist, legacy rejection, batch isolation and
authenticated read routes. A separate in-memory manual check exercised archive,
restore, edits and second archive, confirming the first payload remained intact;
another checked the legacy migration and repeat/bootstrap path. No existing
traffic or archive memberships were changed for verification. Browser checks use
an isolated in-memory fixture for populated snapshots and the actual existing
legacy batches for the totals-only state. These do not verify VM ingestion.
