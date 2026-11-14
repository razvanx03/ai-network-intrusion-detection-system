import importlib.util
import asyncio
from functools import wraps
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
import sys
import httpx
import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from app.schemas.reset import ResetRequest
from app.repositories.reset_repository import ResetRepository, ResetBusyError
from app.services.reset_service import ResetService
from app.services.analysis_service import AnalysisBusyError, AnalysisService
from app.integrations.sensor_client import SensorClient, SensorResetError

ID = "a" * 32


def run_async(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        return asyncio.run(function(*args, **kwargs))
    return wrapped


@pytest.fixture
def reset_service(db, monkeypatch):
    service = ResetService(db)
    service.resets = MagicMock()
    service.resets.get.return_value = None
    service.sessions = MagicMock()
    service.sessions.running.return_value = None
    sensor = SimpleNamespace(require_reset_support=AsyncMock(), reset_logs=AsyncMock())
    monkeypatch.setattr("app.services.reset_service.sensor_client", sensor)
    return service, sensor


@run_async
async def test_reset_clears_local_data_only_after_vm_acknowledges_and_is_idempotent(reset_service):
    service, sensor = reset_service
    async def remote(operation_id):
        assert operation_id == ID
        service.resets.clear_and_complete.assert_not_called()
        service.db.commit.assert_called_once()
    sensor.reset_logs.side_effect = remote
    assert await service.run(ID) == {"status": "completed"}
    service.resets.clear_and_complete.assert_called_once_with(ID)
    assert service.db.commit.call_count == 2
    service.resets.get.return_value = SimpleNamespace(status="completed")
    await service.run(ID)
    sensor.reset_logs.assert_awaited_once()


@run_async
async def test_remote_failure_preserves_local_data_and_durable_guard(reset_service):
    service, sensor = reset_service
    sensor.reset_logs.side_effect = SensorResetError("reset_sensor_failed")
    with pytest.raises(SensorResetError):
        await service.run(ID)
    service.resets.begin.assert_called_once_with(ID)
    service.db.commit.assert_called_once()
    service.resets.clear_and_complete.assert_not_called()


@run_async
async def test_offline_or_old_agent_does_not_delete_or_start_reset(reset_service):
    service, sensor = reset_service
    sensor.require_reset_support.side_effect = SensorResetError("reset_not_supported")
    with pytest.raises(SensorResetError):
        await service.run(ID)
    service.resets.begin.assert_not_called()
    service.resets.clear_and_complete.assert_not_called()
    sensor.reset_logs.assert_not_called()


@run_async
async def test_running_analysis_or_concurrent_reset_cannot_be_overwritten(reset_service):
    service, sensor = reset_service
    service.sessions.running.return_value = object()
    with pytest.raises(AnalysisBusyError):
        await service.run(ID)
    service.db.rollback.assert_called_once()
    service.db.commit.assert_not_called()
    sensor.reset_logs.assert_not_called()
    service.sessions.running.return_value = None
    service.resets.begin.side_effect = IntegrityError("unit", {}, Exception())
    with pytest.raises(ResetBusyError):
        await service.run(ID)


@run_async
async def test_pending_operation_resumes_same_remote_id_and_local_commit_failure_is_retryable(reset_service):
    service, sensor = reset_service
    service.resets.get.return_value = SimpleNamespace(status="running")
    service.db.commit.side_effect = RuntimeError("unit commit failure")
    with pytest.raises(RuntimeError):
        await service.run(ID)
    service.resets.begin.assert_not_called()
    sensor.reset_logs.assert_awaited_once_with(ID)
    assert service.db.rollback.call_count == 2


def test_clear_removes_traffic_archives_and_cursors_but_preserves_authentication_and_reset_receipts(db):
    db.execute.return_value.rowcount = 1
    ResetRepository(db).clear_and_complete(ID)
    deletes = [call.args[0].table.name for call in db.execute.call_args_list if call.args[0].is_delete]
    assert deletes == ["archive_records", "alert_connections", "analysis_session_connections", "alerts",
        "protocol_events", "connections", "analysis_sessions", "archive_batches", "sensor_cursors", "sensor_file_problems"]
    assert not {"users", "revoked_tokens", "system_resets"}.intersection(deletes)
    db.execute.reset_mock()
    db.execute.return_value.rowcount = 0
    ResetRepository(db).clear_and_complete(ID)
    assert db.execute.call_count == 1  # Completed retries never clear new data.


@run_async
async def test_analysis_checks_reset_guard_under_its_write_lock_before_commit(db, monkeypatch):
    service = AnalysisService(db)
    service.sessions = MagicMock()
    service.sessions.running.return_value = None
    db.scalar.return_value = object()
    with pytest.raises(ResetBusyError):
        await service.run(1, SimpleNamespace(source="sensor"))
    service.sessions.add.assert_called_once()
    db.commit.assert_not_called()
    db.rollback.assert_called_once()


@pytest.mark.parametrize("payload", [
    {"operation_id": ID}, {"operation_id": "../logs", "confirmation": "RESET"},
    {"operation_id": ID, "confirmation": "yes"},
    {"operation_id": ID, "confirmation": "RESET", "path": "/"},
])
def test_reset_requires_exact_confirmation_and_rejects_paths(payload):
    with pytest.raises(ValidationError):
        ResetRequest.model_validate(payload)


@run_async
@pytest.mark.parametrize("receipt", [{"status": "completed", "operation_id": "wrong"},
                                    {"status": "failed", "operation_id": ID}, []])
async def test_sensor_client_rejects_unconfirmed_remote_results(mock_http, receipt):
    mock_http(lambda request: httpx.Response(200, json=receipt))
    with pytest.raises(SensorResetError):
        await SensorClient().reset_logs(ID)


@pytest.fixture
def broker(tmp_path, monkeypatch):
    # Linux locking is a simulated boundary on the Windows test host.
    monkeypatch.setitem(sys.modules, "fcntl", SimpleNamespace(flock=lambda *_: None, LOCK_EX=2))
    path = Path(__file__).resolve().parents[3] / "sensor_agent/reset_logs.py"
    spec = importlib.util.spec_from_file_location("unit_reset_broker", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name, folder in [("LOG_ROOT", "logs"), ("SPOOL_ROOT", "spool"), ("STATE_ROOT", "state")]:
        root = tmp_path / folder
        root.mkdir()
        monkeypatch.setattr(module, name, root)
    monkeypatch.setattr(module, "receipt", lambda path, value: path.write_text(json.dumps(value)))
    def command(*args, **kwargs):
        return 1 if "pgrep" in args[0] and not command.started else 0
    command.started = False
    def control(*args, **kwargs):
        if "start" in args:
            command.started = True
        return command(*args, **kwargs)
    module.command = MagicMock(side_effect=control)
    return module


def test_vm_cleanup_stops_capture_preserves_config_and_never_deletes_new_logs_on_retry(broker):
    (broker.LOG_ROOT / "conn.old.log.gz").write_bytes(b"synthetic")
    (broker.SPOOL_ROOT / "dns.log").write_text("synthetic")
    (broker.SPOOL_ROOT / "state.cfg").write_text("keep")
    assert broker.reset(ID)["status"] == "completed"
    assert not (broker.LOG_ROOT / "conn.old.log.gz").exists()
    assert not (broker.SPOOL_ROOT / "dns.log").exists()
    assert (broker.SPOOL_ROOT / "state.cfg").read_text() == "keep"
    assert broker.command.call_args_list[0].args == ("/usr/bin/systemctl", "stop", "zeek.service")
    (broker.SPOOL_ROOT / "conn.log").write_text("new traffic")
    calls = broker.command.call_count
    broker.reset(ID)
    assert (broker.SPOOL_ROOT / "conn.log").read_text() == "new traffic"
    assert broker.command.call_count == calls


def test_cleaned_receipt_resumes_capture_without_deleting_again(broker):
    (broker.STATE_ROOT / f"{ID}.json").write_text(json.dumps({"phase": "cleaned", "removed": 1}))
    (broker.SPOOL_ROOT / "conn.log").write_text("new traffic")
    broker.reset(ID)
    assert (broker.SPOOL_ROOT / "conn.log").read_text() == "new traffic"
    assert not any("stop" in call.args for call in broker.command.call_args_list)


def test_running_zeek_or_unsafe_root_prevents_deletion(broker):
    (broker.LOG_ROOT / "conn.log").write_text("keep")
    broker.command.side_effect = None
    broker.command.return_value = 0
    with pytest.raises(RuntimeError):
        broker.reset(ID)
    assert (broker.LOG_ROOT / "conn.log").read_text() == "keep"
    with pytest.raises(ValueError):
        broker.reset("../bad")
    with pytest.raises(RuntimeError):
        broker.remove_logs(broker.LOG_ROOT / "missing")


def test_backend_reset_routes_require_cookie_authentication():
    from app.routes.system_routes import router
    from app.routes.deps import get_current_user
    for route in router.routes:
        if route.path.endswith(("/reset-data", "/reset-status")):
            assert any(d.call is get_current_user for d in route.dependant.dependencies)


def test_archival_is_blocked_by_pending_reset_under_its_write_lock(db):
    from app.services.archive_service import ArchiveService
    service = ArchiveService(db)
    service.archives = MagicMock()
    db.scalar.return_value = object()
    with pytest.raises(ResetBusyError):
        service.change()
    service.archives.create.assert_called_once()
    service.archives.archive.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_called_once()
