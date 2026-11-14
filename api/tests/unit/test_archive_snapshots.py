from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException
from app.models.alert import Alert
from app.models.analysis_session import AnalysisSession, AnalysisSessionConnection
from app.models.archive_batch import ArchiveRecord
from app.models.protocol_event import ProtocolEvent
from app.repositories.archive_snapshot_repository import ArchiveSnapshotRepository
from app.routes.archive_routes import require_batch, require_connection, router
from app.routes.deps import get_current_user
from app.services.archive_service import ArchiveService


def test_snapshot_copies_status_context_and_membership_without_live_foreign_keys(db, connection_factory):
    now = datetime.now(timezone.utc)
    batch = SimpleNamespace(id="lot", snapshot_version=None)
    connection = connection_factory(1, created_at=now, archive_batch_id="lot")
    referenced = connection_factory(2, created_at=now, archive_batch_id="older")
    alert = Alert(id=3, timestamp=now, created_at=now, archive_batch_id="lot", connection_id=1,
                  analysis_session_id="session", provenance="analysis", src_ip=connection.src_ip,
                  dst_ip=connection.dst_ip, attack_type="Suspicious Connection", severity="MEDIUM",
                  confidence=.85, detector="unit", description="unit", status="ACKNOWLEDGED")
    alert.connection = connection
    session = AnalysisSession(id="session", source="sensor", status="completed", archive_batch_id="lot",
        detector_status="configured", detector_name="unit", detector_version="v1", preparation_version="v1",
        records_received=1, new_connections_ingested=1, records_prepared=1, new_alerts_detected=1,
        error_code=None, file_issues=[], started_at=now, finished_at=now)
    event = ProtocolEvent(id="event", uid=connection.uid, log_type="dns", ts=1,
                          fields={"query": "example.test", "password": "must-not-be-copied"})
    def scalars(statement):
        result = MagicMock()
        sql = str(statement)
        if sql.startswith("SELECT alert_connections.connection_id"):
            result.all.return_value = [1]
        elif sql.startswith("SELECT connections."):
            result.partitions.return_value = [[connection, referenced]]
        elif sql.startswith("SELECT alerts."):
            result.__iter__.return_value = iter([alert])
        elif sql.startswith("SELECT analysis_sessions."):
            result.__iter__.return_value = iter([session])
        elif sql.startswith("SELECT analysis_session_connections."):
            result.__iter__.return_value = iter([AnalysisSessionConnection(session_id="session", connection_id=1, file="conn.log")])
        elif sql.startswith("SELECT protocol_events."):
            result.__iter__.return_value = iter([event])
        return result
    db.scalars.side_effect = scalars
    writes = []
    def execute(statement, values=None):
        if values:
            writes.extend(values)
        else:
            return [(3, 1)]
    db.execute.side_effect = execute
    with patch("app.repositories.archive_snapshot_repository.ProtocolEventRepository") as context:
        context.return_value.available.return_value = {connection.uid: ["dns"]}
        context.return_value.server_names.return_value = {connection.uid: "archived.test"}
        ArchiveSnapshotRepository(db).capture(batch)
    alert.status = "RESOLVED"
    connection.duration = 99
    event.fields["query"] = "changed.test"
    copied = { (r["kind"], r["record_id"]): r for r in writes }
    assert copied["alert", "3"]["payload"]["status"] == "ACKNOWLEDGED"
    assert copied["connection", "1"]["payload"]["duration"] != 99
    assert copied["connection", "1"]["payload"]["available_logs"] == ["conn", "dns"]
    assert copied["connection", "1"]["payload"]["server_name"] == "archived.test"
    assert copied["connection", "1"]["flagged"] is True
    assert copied["connection", "2"]["member"] is False
    assert copied["event", "event"]["payload"]["fields"] == {"query": "example.test"}
    assert copied["session_connection", "session:1"]["payload"] == {"connection_id": "1", "file": "conn.log"}
    assert copied["alert_connection", "3:1"]["payload"] == {"alert_id": "3"}
    assert batch.snapshot_version == 1
    assert all(fk.target_fullname.startswith("archive_batches.") for fk in ArchiveRecord.__table__.foreign_keys)


@pytest.mark.parametrize("kind,options", [
    ("connection", {"protocols": ["TCP", "udp"], "alerts_only": True}),
    ("connection", {"session_id": "session"}),
    ("event", {"uid": "Cunit", "context": "dns"}),
    ("alert", {"uid": "3"}), ("session", {}),
])
def test_snapshot_queries_scope_rows_and_count_to_batch_without_live_tables(db, kind, options):
    db.scalar.return_value = 0
    db.scalars.return_value.all.return_value = []
    ArchiveSnapshotRepository(db).page("original-lot", kind, 20, 40, **options)
    count = db.scalar.call_args.args[0]
    rows = db.scalars.call_args.args[0]
    assert str(count.whereclause) == str(rows.whereclause)
    assert "original-lot" in rows.compile().params.values()
    assert rows.get_final_froms() == [ArchiveRecord.__table__]
    assert rows._limit_clause.value == 20 and rows._offset_clause.value == 40
    if options.get("protocols"):
        assert ["tcp", "udp"] in rows.compile().params.values()
        assert "flagged IS true" in str(rows)
    if options.get("session_id"):
        assert "session_connection" in rows.compile().params.values()
        assert "session" in rows.compile().params.values()


@pytest.mark.parametrize("batch,code", [(None, 404), (SimpleNamespace(snapshot_version=None), 409)])
def test_old_or_unknown_batches_never_fall_back_to_current_data(db, batch, code):
    db.get.return_value = batch
    with pytest.raises(HTTPException) as error:
        require_batch(db, "lot")
    assert error.value.status_code == code
    db.scalars.assert_not_called()
    if batch:
        assert require_batch(db, "lot", snapshot=False) is batch


def test_connection_details_cannot_escape_requested_batch(db):
    db.get.side_effect = [SimpleNamespace(snapshot_version=1), None]
    with pytest.raises(HTTPException) as error:
        require_connection(db, "lot", 3)
    assert error.value.status_code == 404
    assert db.get.call_args.args[1] == ("lot", "connection", "3")


def test_snapshot_failure_rolls_back_archive_and_restore_does_not_capture_again(db):
    service = ArchiveService(db)
    service.archives = MagicMock()
    service.sessions = MagicMock()
    service.snapshots = MagicMock()
    service.sessions.running.return_value = None
    batch = SimpleNamespace(id="lot", connections=1, alerts=0, sessions=0)
    service.archives.create.return_value = batch
    service.snapshots.capture.side_effect = RuntimeError("snapshot write failed")
    with pytest.raises(RuntimeError):
        service.change()
    service.db.commit.assert_not_called()
    service.db.rollback.assert_called_once()
    service.snapshots.capture.assert_called_once_with(batch)
    service.snapshots.reset_mock()
    service.archives.restore.return_value = batch
    service.change("lot")
    service.snapshots.capture.assert_not_called()


def test_snapshot_reads_are_admin_authenticated_and_never_write_routes():
    for route in router.routes:
        assert any(dependency.call is get_current_user for dependency in route.dependant.dependencies)
        if "/connections" in route.path or "/sessions" in route.path or "/protocols" in route.path:
            assert route.methods == {"GET"}


def test_old_snapshot_server_name_uses_only_frozen_events_and_preserves_payload(db):
    record = SimpleNamespace(payload={"uid": "Cunit", "id": 1})
    events = [SimpleNamespace(parent_id="Cunit", payload={"fields": {"server_name": name}})
              for name in ("", "-", "original.test", "older.test")]
    first = MagicMock()
    first.all.return_value = [record]
    db.scalars.side_effect = [first, events]
    page = ArchiveSnapshotRepository(db).page("original-lot", "connection", 20, 0)
    assert page["items"][0]["server_name"] == "original.test"
    assert "server_name" not in record.payload
    query = db.scalars.call_args.args[0]
    assert "original-lot" in query.compile().params.values()
    assert query.get_final_froms() == [ArchiveRecord.__table__]


@pytest.mark.parametrize("server_name", [None, "frozen.test"])
def test_snapshot_with_saved_server_name_never_enriches_from_current_context(db, server_name):
    record = SimpleNamespace(payload={"uid": "Cunit", "id": 1, "server_name": server_name})
    db.scalars.return_value.all.return_value = [record]
    page = ArchiveSnapshotRepository(db).page("lot", "connection", 20, 0)
    assert page["items"][0]["server_name"] == server_name
    db.scalars.assert_called_once()  # No context lookup, including when name was absent at archival.


def test_old_snapshot_without_tls_name_stays_unavailable_instead_of_guessing(db):
    record = SimpleNamespace(payload={"uid": "Cunit", "id": 1})
    first = MagicMock()
    first.all.return_value = [record]
    db.scalars.side_effect = [first, [SimpleNamespace(parent_id="Cunit", payload={"fields": {}})]]
    page = ArchiveSnapshotRepository(db).page("lot", "connection", 20, 0)
    assert page["items"][0]["server_name"] is None
    assert "server_name" not in record.payload
