"""Collector parsing uses synthetic files and explicit environment only."""
import gzip
import importlib.util
import io
import json
import sys
from pathlib import Path

from fastapi import HTTPException
import pytest


@pytest.fixture
def collector(tmp_path, monkeypatch):
    logs = tmp_path / "logs"
    logs.mkdir()
    (tmp_path / "spool" / "zeek").mkdir(parents=True)
    monkeypatch.setattr("dotenv.dotenv_values", lambda _: {})
    for key, value in {
        "AGENT_HOST": "127.0.0.1", "AGENT_PORT": "8000",
        "API_KEY": "unit-only-collector-credential-not-issued-12345",
        "ZEEK_LOG_DIR": str(logs), "MAX_BATCH_RECORDS": "500",
        "MAX_BATCH_BYTES": "4194304", "MAX_LINE_BYTES": "1048576",
    }.items():
        monkeypatch.setenv(key, value)
    path = Path(__file__).resolve().parents[3] / "sensor_agent" / "collector.py"
    spec = importlib.util.spec_from_file_location("unit_collector", path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, "unit_collector", module)
    spec.loader.exec_module(module)
    return module


def archive(collector, name, content):
    path = collector.LOG_DIR / name
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_bytes(gzip.compress(content))
    return path


def test_blocked_unchanged_archive_is_skipped_before_any_content_read(collector, raw_record, monkeypatch):
    archive(collector, "conn.blocked.log.gz", json.dumps(raw_record).encode() + b"\n" + b"\0" * 20)
    request = collector.FileDiscoveryRequest()
    first = collector.discover_versioned_files(request)["files"][0]
    def forbidden(_):
        raise AssertionError("Unchanged blocked archive must not be opened.")
    monkeypatch.setattr(collector, "open_log", forbidden)
    result = collector.discover_versioned_files(collector.FileDiscoveryRequest(excluded_versions=[first["fingerprint"]]))
    assert result == {"files": [], "issues": [], "empty_files": []}


def test_changed_archive_is_discovered_again_and_version_guard_rejects_stale_read(collector, raw_record):
    path = archive(collector, "conn.changed.log.gz", json.dumps(raw_record).encode() + b"\n")
    first = collector.discover_versioned_files(collector.FileDiscoveryRequest())["files"][0]
    path.write_bytes(gzip.compress(json.dumps({**raw_record, "duration": 99}).encode()+b"\n"))
    second = collector.discover_versioned_files(collector.FileDiscoveryRequest(excluded_versions=[first["fingerprint"]]))["files"][0]
    assert first["fingerprint"] != second["fingerprint"]
    with pytest.raises(HTTPException) as error:
        collector.read_logs(file=first["file"], offset=0, limit=500, file_id=first["file_id"], fingerprint=first["fingerprint"])
    assert error.value.status_code == 409


def test_discovery_failure_has_version_and_empty_repaired_archive_is_explicit(collector):
    path = archive(collector, "conn.bad.log.gz", b"not-json\n")
    result = collector.discover_versioned_files(collector.FileDiscoveryRequest())
    issue = result["issues"][0]
    assert issue["archived"] and len(issue["fingerprint"]) == 64
    path.write_bytes(gzip.compress(b""))
    result = collector.discover_versioned_files(collector.FileDiscoveryRequest(excluded_versions=[issue["fingerprint"]]))
    assert not result["issues"] and result["empty_files"][0]["file"] == issue["file"]


def test_management_routes_require_agent_key_and_exact_confirmation(collector):
    from pydantic import ValidationError
    for route in collector.app.routes:
        if route.path in ("/reset", "/reset/capabilities"):
            assert any(d.call is collector.authenticate for d in route.dependant.dependencies)
    with pytest.raises(ValidationError):
        collector.ResetRequest(operation_id="a" * 32, confirmation="yes")


def test_valid_sealed_json_without_newline_is_accepted(collector, raw_record):
    payload = json.dumps(raw_record).encode()
    archive(collector, "conn.good.log.gz", payload)
    listing = collector.list_files()
    assert listing["issues"] == []
    file = listing["files"][0]
    batch = collector.read_logs(file=file["file"], offset=0, limit=500, file_id=file["file_id"])
    assert batch["records"] == [raw_record]
    assert batch["next_offset"] == len(payload) and not batch["has_more"]


def test_partial_active_record_is_not_consumed(collector, raw_record):
    payload = json.dumps(raw_record).encode()
    archive(collector, "conn.reference.log.gz", payload + b"\n")
    (collector.CURRENT_LOG_DIR / "conn.log").write_bytes(payload)
    assert collector.stream_identity(io.BytesIO(payload), sealed=False) is None
    batch = collector.read_logs(file="current/conn.log", offset=0, limit=500, file_id=None)
    assert batch["records"] == [] and batch["next_offset"] == 0


@pytest.mark.parametrize("broken", [b'{"uid":', b'not-json\n', gzip.compress(b'one')[:10]])
def test_bad_first_record_does_not_hide_healthy_file(collector, raw_record, broken):
    archive(collector, "conn.bad.log.gz", broken)
    archive(collector, "conn.good.log.gz", json.dumps(raw_record).encode() + b"\n")
    listing = collector.list_files()
    assert [f["file"] for f in listing["files"]] == ["conn.good.log.gz"]
    assert listing["issues"] == [{"file": "conn.bad.log.gz", "code": "corrupt_file"}]


def test_partial_archive_tail_returns_typed_file_error_without_partial_batch(collector, raw_record):
    archive(collector, "conn.tail.log.gz", json.dumps(raw_record).encode() + b'\n{"uid":')
    file = collector.list_files()["files"][0]
    with pytest.raises(HTTPException) as error:
        collector.read_logs(file=file["file"], offset=0, limit=500, file_id=file["file_id"])
    assert error.value.status_code == 422
    assert error.value.detail == {"code": "corrupt_file"}


def test_truncated_gzip_is_reported_without_blocking_discovery(collector):
    (collector.LOG_DIR / "conn.broken.log.gz").write_bytes(b'\x1f\x8b\x08')
    assert collector.list_files()["issues"] == [{"file": "conn.broken.log.gz", "code": "corrupt_file"}]


def test_permission_failure_is_reported_as_unreadable(collector, raw_record, monkeypatch):
    archive(collector, "conn.denied.log.gz", json.dumps(raw_record).encode() + b"\n")
    def denied(_):
        raise PermissionError("unit denied")
    monkeypatch.setattr(collector, "open_log", denied)
    assert collector.list_files()["issues"] == [{"file": "conn.denied.log.gz", "code": "unreadable_file"}]


@pytest.mark.parametrize("kind", ["dns", "http", "ssl"])
def test_protocol_current_stream_keeps_identity_across_gzip_rotation(collector, kind):
    payload = json.dumps({"uid": "Cunit", "ts": 100, "query": "example.test"}).encode() + b"\n"
    current = collector.CURRENT_LOG_DIR / f"{kind}.log"
    current.write_bytes(payload)
    initial = collector.list_files()["files"][0]
    assert initial["log_type"] == kind and not initial["archived"]
    archive(collector, f"2026-01-01/{kind}.00-01.log.gz", payload)
    current.unlink()
    rotated = collector.list_files()["files"][0]
    assert initial["file_id"] == rotated["file_id"] and rotated["archived"]
    assert collector.read_logs(file=rotated["file"], offset=0, limit=500, file_id=rotated["file_id"])["records"] == [json.loads(payload)]


def test_identical_first_records_in_different_log_types_are_not_collapsed(collector, raw_record):
    payload = json.dumps(raw_record).encode() + b"\n"
    for kind in ("conn", "dns", "http", "ssl"):
        (collector.CURRENT_LOG_DIR / f"{kind}.log").write_bytes(payload)
    files = collector.list_files()["files"]
    assert len(files) == 4 and len({file["file_id"] for file in files}) == 4


def test_unrelated_log_type_is_not_served(collector):
    (collector.CURRENT_LOG_DIR / "notice.log").write_text('{}\n')
    with pytest.raises(HTTPException) as exc:
        collector.resolve_log_file("current/notice.log")
    assert exc.value.status_code == 400
