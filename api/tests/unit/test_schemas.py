from datetime import datetime, timezone

from pydantic import ValidationError
import pytest

from app.ai.engine import Finding
from app.schemas.analysis import AnalysisRequest, AnalysisSessionResponse
from app.schemas.connection import ZeekLogItem


def test_zeek_aliases_roundtrip_without_mutating_source(raw_record):
    original = raw_record.copy()
    item = ZeekLogItem.model_validate(raw_record)
    assert item.src_ip == raw_record["id.orig_h"]
    assert item.dst_port == 443
    assert ZeekLogItem.model_validate(item.model_dump()) == item
    assert raw_record == original


def test_zeek_missing_values_remain_distinct_from_zero(raw_record):
    raw_record.update(duration="-", orig_bytes="-", service="-", conn_state="-", history="-")
    item = ZeekLogItem.model_validate(raw_record)
    assert item.duration is None and item.orig_bytes is None
    assert item.service is None and item.conn_state is None and item.history is None
    assert item.resp_bytes == 400


@pytest.mark.parametrize("field,value", [
    ("uid", ""), ("uid", "x" * 65), ("ts", -1), ("ts", float("inf")),
    ("ts", float("nan")), ("id.orig_p", -1), ("id.resp_p", 65536),
    ("duration", -0.1), ("duration", float("inf")), ("orig_bytes", -1),
    ("resp_pkts", -1), ("proto", ""),
])
def test_invalid_log_records_fail_validation(field, value, raw_record):
    with pytest.raises(ValidationError):
        ZeekLogItem.model_validate({**raw_record, field: value})


def test_stored_selection_deduplicates_preserving_order():
    assert AnalysisRequest(source="stored", connection_ids=[3, 1, 3, 2]).connection_ids == [3, 1, 2]
    assert AnalysisRequest().source == "sensor"


@pytest.mark.parametrize("values", [
    {"source": "stored"}, {"source": "sensor", "connection_ids": [1]},
    {"source": "unknown"}, {"source": "stored", "connection_ids": [0]},
    {"source": "stored", "connection_ids": [-1]},
    {"source": "stored", "connection_ids": list(range(1, 502))},
])
def test_invalid_analysis_requests_are_rejected(values):
    with pytest.raises(ValidationError):
        AnalysisRequest.model_validate(values)


def test_maximum_stored_selection_is_accepted():
    assert len(AnalysisRequest(source="stored", connection_ids=list(range(1, 501))).connection_ids) == 500


@pytest.mark.parametrize("overrides", [
    {"confidence": -0.1}, {"confidence": 1.1}, {"confidence": float("nan")},
    {"connection_ids": []}, {"connection_ids": list(range(501))},
    {"severity": "UNKNOWN"}, {"timestamp": datetime(2026, 1, 1)},
    {"description": ""},
])
def test_invalid_findings_cannot_be_persisted(overrides):
    values = dict(connection_ids=[1], timestamp=datetime.now(timezone.utc),
                  attack_type="Suspicious Connection", severity="MEDIUM", confidence=0.8,
                  description="connection_model_review")
    with pytest.raises(ValidationError):
        Finding.model_validate({**values, **overrides})


def test_sqlite_naive_session_timestamps_are_explicit_utc():
    timestamp = datetime(2026, 1, 1)
    session = AnalysisSessionResponse(
        id="session", source="stored", status="completed", detector_status="configured",
        detector_name="unit", detector_version=None, preparation_version="unit",
        records_received=1, new_connections_ingested=0, records_prepared=1,
        new_alerts_detected=0, error_code=None, started_at=timestamp, finished_at=timestamp,
    )
    assert session.started_at.tzinfo == timezone.utc
    assert session.finished_at.tzinfo == timezone.utc
