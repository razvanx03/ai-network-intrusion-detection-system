import asyncio
import json

import httpx
import pytest

from app.integrations.sensor_client import SensorClient, SensorFile


@pytest.fixture
def sensor():
    return SensorClient()


@pytest.fixture
def file():
    return SensorFile(file="2026-01-01/conn.10-11.log.gz", file_id="a" * 64,
                      archived=True, first_ts=1700000000)


def test_file_discovery_sends_api_key_and_validates_metadata(sensor, file, mock_http):
    requests = mock_http(lambda request: httpx.Response(200, json={"files": [file.model_dump()]}))
    assert asyncio.run(sensor.list_files()) == [file]
    assert requests[0].url.path == "/files"
    assert requests[0].headers["X-API-Key"] == "unit-only-sensor-key"


def batch_payload(source_file, **changes):
    return {"file": source_file.file, "file_id": source_file.file_id, "offset": 100,
            "next_offset": 200, "has_more": False, "records_returned": 1,
            "records": [{"uid": "unit"}], **changes}


def test_read_file_sends_identity_and_offset(sensor, file, mock_http):
    requests = mock_http(lambda request: httpx.Response(200, json=batch_payload(file)))
    result = asyncio.run(sensor.read_file(file, 100))
    assert result.next_offset == 200
    assert dict(requests[0].url.params) == {
        "file": file.file, "file_id": file.file_id, "offset": "100", "limit": "500"}
    assert requests[0].headers["X-API-Key"] == sensor.api_key


@pytest.mark.parametrize("changes", [
    {"file": "other.log"}, {"file_id": "b" * 64}, {"offset": 99},
    {"next_offset": 99}, {"records_returned": 2}, {"next_offset": 100},
    {"records": [], "records_returned": 0, "has_more": True, "next_offset": 100},
])
def test_inconsistent_sensor_cursor_is_rejected(sensor, file, changes, mock_http):
    mock_http(lambda request: httpx.Response(200, json=batch_payload(file, **changes)))
    with pytest.raises(RuntimeError, match="inconsistent file cursor"):
        asyncio.run(sensor.read_file(file, 100))


def test_empty_end_of_file_may_preserve_offset(sensor, file, mock_http):
    mock_http(lambda request: httpx.Response(200, json=batch_payload(
        file, records=[], records_returned=0, next_offset=100)))
    assert asyncio.run(sensor.read_file(file, 100)).records == []


@pytest.mark.parametrize("status", [401, 403, 404, 500])
def test_sensor_http_failures_are_not_empty_successes(sensor, status, mock_http):
    mock_http(lambda request: httpx.Response(status, json={"detail": "unit failure"}))
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(sensor.list_files())


def test_sensor_transport_failure_propagates(sensor, mock_http):
    def disconnected(request):
        raise httpx.ConnectError("unit disconnected", request=request)
    mock_http(disconnected)
    with pytest.raises(httpx.ConnectError):
        asyncio.run(sensor.list_files())


def test_sample_progress_requires_acknowledgment(sensor, tmp_path):
    sensor.mock_mode = True
    sensor.samples_dir = tmp_path
    for index in range(1, 4):
        (tmp_path / f"zeek_sample_batch{index}.json").write_text(
            json.dumps([{"uid": f"unit-{index}"}]), encoding="utf-8")

    async def scenario():
        first = await sensor.fetch_new_logs()
        assert await sensor.fetch_new_logs() == first
        await sensor.acknowledge("wrong-batch")
        assert await sensor.fetch_new_logs() == first
        await sensor.acknowledge(first.batch_id)
        assert (await sensor.fetch_new_logs()).records == [{"uid": "unit-2"}]
        await sensor.acknowledge(first.batch_id)  # Duplicate ACK cannot skip another batch.
        assert sensor._mock_step == 1
        await sensor.reset_sensor_logs()
        assert await sensor.fetch_new_logs() == first
    asyncio.run(scenario())


@pytest.mark.parametrize("operation,args", [("fetch_new_logs", ()),
    ("acknowledge", ("batch",)), ("reset_sensor_logs", ())])
def test_remote_mode_cannot_use_legacy_mock_cursor_operations(sensor, operation, args):
    with pytest.raises(RuntimeError):
        asyncio.run(getattr(sensor, operation)(*args))


def test_missing_sample_fails_fast(sensor, tmp_path):
    sensor.mock_mode, sensor.samples_dir = True, tmp_path
    with pytest.raises(FileNotFoundError):
        asyncio.run(sensor.fetch_new_logs())


def test_corrupt_sample_fails_fast(sensor, tmp_path):
    sensor.mock_mode, sensor.samples_dir = True, tmp_path
    (tmp_path / "zeek_sample_batch1.json").write_text("{broken-json", encoding="utf-8")
    with pytest.raises(ValueError, match="Corrupt"):
        asyncio.run(sensor.fetch_new_logs())
