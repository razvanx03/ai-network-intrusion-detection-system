import asyncio
from unittest.mock import AsyncMock, MagicMock
from app.services import system_service as module
from app.services.system_service import SystemService
from app.schemas.analysis import AnalysisRequest
from types import SimpleNamespace
import httpx
import pytest


def test_manual_fetch_delegates_to_analysis_without_changing_progress(db, monkeypatch):
    analysis = MagicMock()
    analysis.run = AsyncMock(return_value={"status": "success"})
    monkeypatch.setattr(module, "AnalysisService", lambda _: analysis)
    assert asyncio.run(SystemService(db).fetch_and_analyze(7)) == {"status": "success"}
    analysis.run.assert_awaited_once_with(7, AnalysisRequest())
    db.execute.assert_not_called()


def test_overview_delegates_to_active_data_summary(db, monkeypatch):
    repository = MagicMock()
    repository.summary.return_value = {"connections_total": 3}
    monkeypatch.setattr(module, "OverviewRepository", lambda _: repository)
    assert SystemService(db).overview() == {"connections_total": 3}


def test_no_reset_or_delete_operations_remain():
    assert not hasattr(SystemService, "clear_database_all")
    assert not hasattr(SystemService, "reset_sensor")


@pytest.mark.parametrize("response,expected", [
    (httpx.Response(200, json={"status": "ok", "service": "zeek-sensor-agent"}), "available"),
    (httpx.Response(200, json={"status": "ok", "service": "other"}), "invalid_response"),
    (httpx.Response(200, json=[]), "invalid_response"),
    (httpx.Response(200, text="invalid json"), "invalid_response"),
    (httpx.Response(401), "unauthorized"), (httpx.Response(403), "unauthorized"),
    (httpx.Response(503), "unavailable"),
])
def test_sensor_status_reports_probe_results_without_reading_logs(db, monkeypatch, response, expected):
    sensor = SimpleNamespace(mock_mode=False, health=AsyncMock(return_value=response))
    monkeypatch.setattr(module, "sensor_client", sensor)
    result = asyncio.run(SystemService(db).sensor_status())
    assert result["status"] == expected
    assert result["checked_at"].tzinfo is not None
    sensor.health.assert_awaited_once()
    db.execute.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("host,expected", [("reachable", "unavailable"), ("unreachable", "host_unreachable"), ("unknown", "host_unknown")])
def test_sensor_timeout_distinguishes_agent_and_host_without_logging_out(db, monkeypatch, host, expected):
    sensor = SimpleNamespace(mock_mode=False, health=AsyncMock(side_effect=httpx.ConnectTimeout("unit timeout")), host_status=AsyncMock(return_value=host))
    monkeypatch.setattr(module, "sensor_client", sensor)
    assert asyncio.run(SystemService(db).sensor_status())["status"] == expected
    sensor.host_status.assert_awaited_once()


def test_sample_mode_does_not_claim_ubuntu_is_operational(db, monkeypatch):
    sensor = SimpleNamespace(mock_mode=True, health=AsyncMock())
    monkeypatch.setattr(module, "sensor_client", sensor)
    assert asyncio.run(SystemService(db).sensor_status())["status"] == "sample_mode"
    sensor.health.assert_not_awaited()
