import asyncio
import json

import httpx
import pytest

from app.integrations.sensor_client import SensorClient, SensorFile, SensorFileError


@pytest.fixture
def sensor():
    return SensorClient()


@pytest.fixture
def file():
    return SensorFile(file="2026-01-01/conn.10-11.log.gz", file_id="a" * 64,
                      archived=True, first_ts=1700000000, fingerprint="f" * 64)


def test_health_probe_is_authenticated_bounded_and_does_not_fetch_logs(sensor, mock_http):
    requests = mock_http(lambda _: httpx.Response(200, json={"status": "ok", "service": "zeek-sensor-agent"}))
    response = asyncio.run(sensor.health())
    assert response.status_code == 200 and len(requests) == 1
    request = requests[0]
    assert request.method == "GET" and request.url.path == "/health"
    assert request.headers["X-API-Key"] == "unit-only-sensor-key"
    assert all(value == 5.0 for value in request.extensions["timeout"].values())


def test_file_discovery_sends_api_key_and_validates_metadata(sensor, file, mock_http):
    requests = mock_http(lambda request: httpx.Response(200, json={"files": [file.model_dump()]}))
    assert asyncio.run(sensor.list_files()) == [file]
    assert requests[0].url.path == "/files/discover"
    assert requests[0].headers["X-API-Key"] == "unit-only-sensor-key"


def test_discovery_preserves_explicit_file_issues(sensor, file, mock_http):
    mock_http(lambda _: httpx.Response(200, json={"files": [file.model_dump()],
        "issues": [{"file": "broken.log.gz", "code": "corrupt_file"}]}))
    result = asyncio.run(sensor.discover_files())
    assert result.files == [file] and result.issues[0].file == "broken.log.gz"


@pytest.mark.parametrize("code", ["corrupt_file", "unreadable_file", "oversized_file"])
def test_typed_file_failure_can_be_skipped(sensor, file, mock_http, code):
    mock_http(lambda _: httpx.Response(422, json={"detail": {"code": code}}))
    with pytest.raises(SensorFileError) as error:
        asyncio.run(sensor.read_file(file, 100))
    assert error.value.issue.code == code
    assert error.value.issue.offset == 100 and error.value.issue.file == file.file


def test_unrecognized_422_remains_a_failure(sensor, file, mock_http):
    mock_http(lambda _: httpx.Response(422, json={"detail": "Unexpected protocol failure"}))
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(sensor.read_file(file, 100))


@pytest.mark.parametrize("status", [401, 403, 409, 500])
def test_non_file_failures_are_not_skipped(sensor, file, mock_http, status):
    mock_http(lambda _: httpx.Response(status, json={"detail": {"code": "corrupt_file"}}))
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(sensor.read_file(file, 100))


def batch_payload(source_file, **changes):
    return {"file": source_file.file, "file_id": source_file.file_id, "offset": 100,
            "next_offset": 200, "has_more": False, "records_returned": 1,
            "records": [{"uid": "unit"}], **changes}


def test_read_file_sends_identity_and_offset(sensor, file, mock_http):
    requests = mock_http(lambda request: httpx.Response(200, json=batch_payload(file)))
    result = asyncio.run(sensor.read_file(file, 100))
    assert result.next_offset == 200
    assert dict(requests[0].url.params) == {
        "file": file.file, "file_id": file.file_id, "offset": "100", "limit": "500", "fingerprint": "f" * 64}
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
    asyncio.run(scenario())


@pytest.mark.parametrize("operation,args", [("fetch_new_logs", ()),
    ("acknowledge", ("batch",))])
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


def test_discovery_sends_excluded_versions_and_preserves_repaired_empty_archives(sensor, mock_http):
    versions = ["a" * 64, "b" * 64]
    requests = mock_http(lambda _: httpx.Response(200, json={"files": [], "empty_files": [
        {"file": "day/dns.log.gz", "fingerprint": "c" * 64}]}))
    result = asyncio.run(sensor.discover_files(versions))
    assert requests[0].method == "POST"
    assert json.loads(requests[0].content) == {"excluded_versions": versions}
    assert result.empty_files[0].file == "day/dns.log.gz"
    assert result.empty_files[0].fingerprint == "c" * 64


def test_discovery_exclusion_limit_fails_before_network_request(sensor, mock_http):
    requests = mock_http(lambda _: pytest.fail("Oversized exclusion lists must not be sent"))
    with pytest.raises(RuntimeError, match="Too many blocked"):
        asyncio.run(sensor.discover_files(["a" * 64] * 10001))
    assert requests == []


@pytest.mark.parametrize("fingerprint", [None, "", "not-a-fingerprint", "A" * 64])
def test_discovery_rejects_missing_or_invalid_version_instead_of_using_legacy_protocol(sensor, file, mock_http, fingerprint):
    from pydantic import ValidationError
    payload = file.model_dump()
    if fingerprint is None:
        payload.pop("fingerprint")
    else:
        payload["fingerprint"] = fingerprint
    requests = mock_http(lambda _: httpx.Response(200, json={"files": [payload]}))
    with pytest.raises(ValidationError):
        asyncio.run(sensor.discover_files())
    assert len(requests) == 1  # No fallback GET /files or fabricated empty result.


def test_current_file_reads_do_not_require_a_stable_archive_fingerprint(sensor, file, mock_http):
    current = file.model_copy(update={"file": "current/conn.log", "archived": False})
    requests = mock_http(lambda _: httpx.Response(200, json=batch_payload(current)))
    asyncio.run(sensor.read_file(current, 100))
    assert "fingerprint" not in requests[0].url.params


@pytest.mark.parametrize("archived", [True, False])
def test_typed_read_error_preserves_version_and_archive_metadata(sensor, file, mock_http, archived):
    source = file.model_copy(update={"archived": archived})
    mock_http(lambda _: httpx.Response(422, json={"detail": {"code": "oversized_file"}}))
    with pytest.raises(SensorFileError) as error:
        asyncio.run(sensor.read_file(source, 100))
    assert error.value.issue.archived is archived
    assert error.value.issue.fingerprint == source.fingerprint
