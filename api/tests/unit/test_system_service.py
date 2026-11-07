import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services import system_service as module
from app.services.analysis_service import AnalysisBusyError
from app.services.system_service import SystemService


@pytest.fixture
def system(db, monkeypatch):
    service = SystemService(db)
    service.sessions = MagicMock()
    service.sessions.running.return_value = None
    service.conn_repo = MagicMock()
    service.alert_repo = MagicMock()
    service.cursor_repo = MagicMock()
    sensor = SimpleNamespace(mock_mode=False, base_url="https://sensor.invalid",
                             api_key="unit-key", reset_sensor_logs=AsyncMock())
    monkeypatch.setattr(module, "sensor_client", sensor)
    return service, sensor


def test_reset_remote_progress_only_updates_backend_cursors(system):
    service, sensor = system
    assert asyncio.run(service.reset_sensor())["status"] == "success"
    service.cursor_repo.reset.assert_called_once_with(sensor.base_url)
    sensor.reset_sensor_logs.assert_not_awaited()
    service.db.commit.assert_called_once()


def test_reset_sample_progress_does_not_delete_remote_cursors(system):
    service, sensor = system
    sensor.mock_mode = True
    asyncio.run(service.reset_sensor())
    sensor.reset_sensor_logs.assert_awaited_once()
    service.cursor_repo.reset.assert_not_called()


@pytest.mark.parametrize("operation", ["clear", "reset"])
def test_destructive_operations_refuse_while_analysis_is_running(system, operation):
    service, sensor = system
    service.sessions.running.return_value = object()
    with pytest.raises(AnalysisBusyError):
        if operation == "clear":
            service.clear_database_all()
        else:
            asyncio.run(service.reset_sensor())
    service.sessions.delete_history.assert_not_called()
    service.cursor_repo.reset.assert_not_called()
    service.db.commit.assert_not_called()
    sensor.reset_sensor_logs.assert_not_awaited()


def test_clear_database_is_one_transaction_and_preserves_read_progress(system):
    service, _ = system
    service.alert_repo.delete_all.return_value = 3
    service.conn_repo.delete_all.return_value = 10
    result = service.clear_database_all()
    assert result["deleted_connections"] == 10 and result["deleted_alerts"] == 3
    service.alert_repo.delete_all.assert_called_once_with(commit=False)
    service.conn_repo.delete_all.assert_called_once_with(commit=False)
    service.cursor_repo.reset.assert_not_called()
    service.sessions.delete_history.assert_called_once()
    service.db.commit.assert_called_once()


@pytest.mark.parametrize("failure_at", ["history", "alerts", "connections", "commit"])
def test_clear_database_rolls_back_and_propagates_failures(system, failure_at):
    service, _ = system
    operation = {"history": service.sessions.delete_history,
                 "alerts": service.alert_repo.delete_all,
                 "connections": service.conn_repo.delete_all,
                 "commit": service.db.commit}[failure_at]
    operation.side_effect = RuntimeError("unit write failed")
    with pytest.raises(RuntimeError, match="unit write failed"):
        service.clear_database_all()
    service.db.rollback.assert_called_once()
