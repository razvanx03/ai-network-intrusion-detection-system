from datetime import datetime, timezone
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.protocol_event import normalize_event
from app.services.ingestion_service import IngestionService, IngestionBatch
from app.services.connection_service import ConnectionService
from app.repositories.protocol_event_repository import ProtocolEventRepository


def test_multiple_dns_transactions_for_one_uid_keep_distinct_identities():
    first = {"uid": "Cunit", "ts": 100.0, "query": "example.test", "answers": ["192.0.2.1"]}
    second = {**first, "query": "other.test"}
    assert normalize_event("dns", first)["id"] != normalize_event("dns", second)["id"]
    assert normalize_event("dns", first) == normalize_event("dns", dict(reversed(list(first.items()))))
    assert normalize_event("dns", first)["id"] != normalize_event("http", first)["id"]


def test_http_context_excludes_credentials_and_bodies():
    result = normalize_event("http", {"uid": "Cunit", "ts": 100, "method": "GET", "host": "example.test",
                                      "username": "private", "password": "private", "authorization": "private", "body": "private"})
    assert result["fields"] == {"method": "GET", "host": "example.test"}


@pytest.mark.parametrize("changes", [{"uid": ""}, {"ts": float("nan")}, {"ts": -1}, {"uid": "x" * 65}])
def test_invalid_context_identity_is_rejected(changes):
    with pytest.raises((ValidationError, ValueError)):
        normalize_event("dns", {"uid": "Cunit", "ts": 100, **changes})


def test_context_persist_does_not_require_or_create_a_connection(db, monkeypatch):
    repo = MagicMock()
    monkeypatch.setattr("app.services.ingestion_service.ProtocolEventRepository", lambda _: repo)
    service = IngestionService(db)
    service.cursors = MagicMock()
    service.connections = MagicMock()
    assert service.persist(IngestionBatch(records=[{"uid": "Clate", "ts": 100, "server_name": "example.test"}],
        log_type="ssl", sensor_url="unit", file_id="a" * 64, file="ssl.log", next_offset=80)) == []
    assert repo.create_batch.call_args.args[0][0]["uid"] == "Clate"
    service.connections.create_batch.assert_not_called()
    service.cursors.advance.assert_called_once_with("unit", "a" * 64, "ssl.log", 0, 80, False)
    db.commit.assert_not_called()  # The orchestration commits context and progress together.


def test_invalid_context_cannot_advance_progress(db):
    service = IngestionService(db)
    service.cursors = MagicMock()
    with pytest.raises(ValidationError):
        service.persist(IngestionBatch(records=[{"ts": 100}], log_type="dns", file_id="a" * 64))
    service.cursors.advance.assert_not_called()
    db.execute.assert_not_called()


def test_replayed_events_are_ignored_by_unique_content_id(db):
    ProtocolEventRepository(db).create_batch([normalize_event("dns", {"uid": "Cunit", "ts": 100, "query": "example.test"})])
    assert "ON CONFLICT (id) DO NOTHING" in str(db.execute.call_args.args[0])


def test_context_is_looked_up_by_uid_and_paged_without_exposing_other_uids(db):
    db.scalar.return_value = 1
    db.scalars.return_value.all.return_value = []
    result = ProtocolEventRepository(db).page("Cunit", "dns", 50, 10)
    statement = db.scalars.call_args.args[0].compile().params
    assert "Cunit" in statement.values() and "dns" in statement.values()
    assert result == {"items": [], "total": 1, "limit": 50, "offset": 10}


def test_deleted_connection_details_return_404(db):
    db.get.return_value = None
    with pytest.raises(HTTPException) as exc:
        ConnectionService(db).events(99, "dns", 50, 0)
    assert exc.value.status_code == 404


def test_connection_list_includes_available_context_without_changing_record(db, connection_factory, monkeypatch):
    repo = MagicMock()
    repo.available.return_value = {"Cunit1": ["ssl", "dns"]}
    repo.server_names.return_value = {"Cunit1": "example.test"}
    monkeypatch.setattr("app.services.connection_service.ProtocolEventRepository", lambda _: repo)
    connection = connection_factory(created_at=datetime.now(timezone.utc))
    response = ConnectionService(db).with_context([connection])[0]
    assert response.available_logs == ["conn", "dns", "ssl"]
    assert response.server_name == "example.test"
    assert response.uid == connection.uid
    assert not hasattr(connection, "available_logs")


def test_server_names_query_is_batched_and_selects_latest_nonempty_tls_name(db):
    db.execute.return_value = [("Cunit1", " example.test ")]
    assert ProtocolEventRepository(db).server_names(["Cunit1", "Cunit2"]) == {"Cunit1": "example.test"}
    statement = db.execute.call_args.args[0]
    sql = str(statement)
    assert "row_number() OVER (PARTITION BY protocol_events.uid ORDER BY protocol_events.ts DESC" in sql
    assert ["Cunit1", "Cunit2"] in statement.compile().params.values()
    assert "ssl" in statement.compile().params.values()
    db.execute.reset_mock()
    assert ProtocolEventRepository(db).server_names([]) == {}
    db.execute.assert_not_called()


def test_session_connection_page_enriches_context_without_losing_import_link(db, connection_factory, monkeypatch):
    from types import SimpleNamespace
    from app.routes.analysis_routes import session_connections
    connection = connection_factory(created_at=datetime.now(timezone.utc))
    repo = MagicMock()
    repo.get.return_value = SimpleNamespace(archive_batch_id=None)
    repo.connection_page.return_value = ([(connection, SimpleNamespace(file_id="stream", file="conn.log"))], 1)
    monkeypatch.setattr("app.routes.analysis_routes.AnalysisRepository", lambda _: repo)
    context = MagicMock()
    context.available.return_value = {connection.uid: ["ssl"]}
    context.server_names.return_value = {connection.uid: "example.test"}
    monkeypatch.setattr("app.services.connection_service.ProtocolEventRepository", lambda _: context)
    page = session_connections("session", limit=20, offset=0, include_archived=False, db=db)
    assert page["items"][0]["connection"].server_name == "example.test"
    assert page["items"][0]["connection"].available_logs == ["conn", "ssl"]
    assert page["items"][0]["file"] == "conn.log"


def test_batched_enrichment_keeps_names_with_their_uid_and_does_not_guess_missing_names(db, connection_factory, monkeypatch):
    repo = MagicMock()
    repo.available.return_value = {"Cunit1": ["ssl"], "Cunit2": ["dns"]}
    repo.server_names.return_value = {"Cunit1": "first.test"}
    monkeypatch.setattr("app.services.connection_service.ProtocolEventRepository", lambda _: repo)
    connections = [connection_factory(i, created_at=datetime.now(timezone.utc)) for i in [2, 1, 3]]
    response = ConnectionService(db).with_context(connections)
    assert [c.uid for c in response] == ["Cunit2", "Cunit1", "Cunit3"]
    assert [c.server_name for c in response] == [None, "first.test", None]
    assert [c.available_logs for c in response] == [["conn", "dns"], ["conn", "ssl"], ["conn"]]
    repo.available.assert_called_once_with(["Cunit2", "Cunit1", "Cunit3"])
    repo.server_names.assert_called_once_with(["Cunit2", "Cunit1", "Cunit3"])


def test_empty_connection_page_does_not_query_protocol_events(db):
    assert ConnectionService(db).with_context([]) == []
    db.execute.assert_not_called()
