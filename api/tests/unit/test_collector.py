"""Collector parsing uses synthetic files and explicit environment only."""
import gzip
import importlib.util
import io
import json
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
    spec.loader.exec_module(module)
    return module


def archive(collector, name, content):
    path = collector.LOG_DIR / name
    path.parent.mkdir(exist_ok=True, parents=True)
    path.write_bytes(gzip.compress(content))
    return path


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
