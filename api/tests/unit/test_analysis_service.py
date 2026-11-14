import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx
import pytest
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.ai.engine import Finding, UnconfiguredDetector
from app.repositories.sensor_cursor_repository import CursorConflictError
from app.schemas.analysis import AnalysisRequest
from app.services import analysis_service as module
from app.services.analysis_service import (
    AnalysisBusyError, AnalysisRunError, AnalysisService, InvalidRecordsError,
)
from app.services.ingestion_service import IngestionBatch
from app.schemas.sensor import SensorFileIssue


@pytest.fixture
def analysis(db, monkeypatch, raw_record):
    service = AnalysisService(db)
    service.sessions = MagicMock()
    service.sessions.running.return_value = None
    service.alerts = MagicMock()
    service.ingestion = MagicMock()
    async def initial_batch():
        yield IngestionBatch(records=[raw_record])
    service.ingestion.batches.side_effect = lambda: initial_batch()
    detector = SimpleNamespace(name="unit-detector", version="v1", configured=True,
                               analyze_batch=MagicMock(return_value=[]))
    monkeypatch.setattr(module.engine, "analysis_engine", detector)
    monkeypatch.setattr(module, "uuid4", lambda: SimpleNamespace(hex="unit-session"))
    session = SimpleNamespace(
        id="unit-session", source="sensor", status="running", detector_status="configured",
        detector_name=detector.name, detector_version=detector.version,
        preparation_version=module.PREPARATION_VERSION, records_received=0,
        new_connections_ingested=0, records_prepared=0, new_alerts_detected=0,
        error_code=None, started_at=datetime.now(timezone.utc), finished_at=None,
    )

    def record_batch(session_id, received, imported, prepared, alerts):
        session.records_received += received
        session.new_connections_ingested += imported
        session.records_prepared += prepared
        session.new_alerts_detected += alerts

    def finish(session_id, status, code=None):
        session.status, session.error_code = status, code
        session.finished_at = datetime.now(timezone.utc)

    service.sessions.record_batch.side_effect = record_batch
    service.sessions.finish.side_effect = finish
    service.sessions.get.return_value = session
    return service, detector, session


def finding(ids=None, **changes):
    return Finding(connection_ids=ids or [1], timestamp=datetime.now(timezone.utc),
                   attack_type="Suspicious Connection", severity="MEDIUM", confidence=0.8,
                   description="connection_model_review", **changes)


def sensor_request():
    return AnalysisRequest()


def test_already_reported_file_issue_does_not_repeat_session_warning(analysis):
    service, detector, session = analysis
    session.file_issues = []
    issue = SensorFileIssue(file="old/conn.log.gz", code="corrupt_file",
                            archived=True, fingerprint="a" * 64, offset=333)

    async def batches():
        yield IngestionBatch(records=[], issue=issue)

    service.ingestion.batches.side_effect = lambda: batches()
    service.ingestion.note_issue.return_value = False
    result = asyncio.run(service.run(7, sensor_request()))
    assert result["analysis_session"].status == "completed"
    assert result["analysis_session"].file_issues == []
    assert result["new_connections_ingested"] == result["new_alerts_detected"] == 0
    service.sessions.record_file_issue.assert_not_called()
    service.ingestion.persist.assert_not_called()
    detector.analyze_batch.assert_not_called()


def test_problem_history_failure_is_not_reported_as_successful_analysis(analysis):
    service, detector, _ = analysis

    async def batches():
        yield IngestionBatch(records=[], issue=SensorFileIssue(file="old/conn.log.gz", code="corrupt_file"))

    service.ingestion.batches.side_effect = lambda: batches()
    service.ingestion.note_issue.side_effect = SQLAlchemyError("unit history write failure")
    with pytest.raises(AnalysisRunError) as error:
        asyncio.run(service.run(7, sensor_request()))
    assert error.value.code == "processing_failed"
    service.sessions.finish.assert_called_once_with("unit-session", "failed", "processing_failed")
    service.sessions.record_file_issue.assert_not_called()
    service.db.rollback.assert_called_once()
    detector.analyze_batch.assert_not_called()


def test_protocol_context_is_committed_without_calling_classifier(analysis):
    service, detector, _ = analysis
    async def batches():
        yield IngestionBatch(records=[{"uid": "Cunit", "ts": 100, "query": "example.test"}], log_type="dns")
    service.ingestion.batches = batches
    service.ingestion.persist.return_value = []
    result = asyncio.run(service.run(7, AnalysisRequest(source="sensor")))
    detector.analyze_batch.assert_not_called()
    service.sessions.record_batch.assert_not_called()
    assert result["new_connections_ingested"] == 0 and result["new_alerts_detected"] == 0
    assert result["analysis_session"].status == "completed"


def test_sensor_analysis_emits_traceable_finding(analysis, connection_factory):
    service, detector, _ = analysis
    connection = connection_factory()
    service.ingestion.persist.return_value = [connection]
    detector.analyze_batch.return_value = [finding()]
    service.alerts.create_batch.return_value = [SimpleNamespace(id=9)]
    result = asyncio.run(service.run(7, sensor_request()))
    assert result["new_connections_ingested"] == 1
    assert result["new_alerts_detected"] == 1 and result["alerts_summary"] == {"MEDIUM": 1}
    assert result["analysis_session"].status == "completed"
    values = service.alerts.create_batch.call_args.args[0][0]
    assert values["connection_id"] == connection.id
    assert values["src_ip"] == connection.src_ip
    assert values["analysis_session_id"] == "unit-session" and values["provenance"] == "analysis"
    assert values["detector"] == detector.name and values["status"] == "NEW"
    service.alerts.link_connections.assert_called_once_with(9, [1])
    service.ingestion.persist.assert_called_once()
    assert service.db.commit.call_count == 3
    service.db.rollback.assert_not_called()


def test_aggregate_finding_deduplicates_evidence_and_has_no_single_connection(analysis, connection_factory):
    service, detector, _ = analysis
    detector.analyze_batch.return_value = [finding([2, 1, 2])]
    service.alerts.create_batch.return_value = [SimpleNamespace(id=9)]
    summary = {}
    service._process("unit-session", [connection_factory(1), connection_factory(2)], 2, 0, detector, summary)
    assert service.alerts.create_batch.call_args.args[0][0]["connection_id"] is None
    service.alerts.link_connections.assert_called_once_with(9, [2, 1])
    service.sessions.record_batch.assert_called_once_with("unit-session", 2, 0, 2, 1)
    assert summary == {"MEDIUM": 1}


def test_finding_cannot_reference_connections_outside_batch(analysis, connection_factory):
    service, detector, _ = analysis
    detector.analyze_batch.return_value = [finding([999])]
    with pytest.raises(ValueError, match="this batch"):
        service._process("unit-session", [connection_factory()], 1, 0, detector, {})
    service.alerts.create_batch.assert_not_called()
    service.sessions.record_batch.assert_not_called()


def test_unconfigured_detector_cannot_emit_findings(analysis, connection_factory):
    service, detector, _ = analysis
    detector.configured = False
    detector.analyze_batch.return_value = [finding()]
    with pytest.raises(ValueError, match="unconfigured detector"):
        service._process("unit-session", [connection_factory()], 1, 0, detector, {})
    service.alerts.create_batch.assert_not_called()


def test_unconfigured_analysis_is_recorded_without_safety_verdict(analysis, connection_factory, monkeypatch):
    service, _, _ = analysis
    monkeypatch.setattr(module.engine, "analysis_engine", UnconfiguredDetector())
    service.ingestion.persist.return_value = [connection_factory()]
    result = asyncio.run(service.run(7, sensor_request()))
    assert result["new_alerts_detected"] == 0
    assert service.sessions.add.call_args.kwargs["detector_status"] == "not_configured"
    service.alerts.create_batch.assert_not_called()


def test_bad_imported_record_is_classified_as_invalid_records(analysis, connection_factory):
    service, detector, _ = analysis
    service.ingestion.persist.return_value = [connection_factory(duration=-1)]
    with pytest.raises(AnalysisRunError) as error:
        asyncio.run(service.run(7, sensor_request()))
    assert error.value.code == "invalid_records"
    detector.analyze_batch.assert_not_called()
    service.db.rollback.assert_called_once()


def test_busy_analysis_cannot_create_another_session(analysis):
    service, _, _ = analysis
    service.sessions.running.return_value = object()
    with pytest.raises(AnalysisBusyError):
        asyncio.run(service.run(7, sensor_request()))
    service.sessions.add.assert_not_called()
    service.db.commit.assert_not_called()


@pytest.mark.parametrize("raced", [True, False])
def test_session_creation_race_rolls_back_and_only_masks_real_busy_conflicts(analysis, raced):
    service, _, _ = analysis
    service.sessions.running.side_effect = [None, object() if raced else None]
    service.sessions.add.side_effect = IntegrityError("insert", {}, RuntimeError("unit conflict"))
    with pytest.raises(AnalysisBusyError if raced else IntegrityError):
        asyncio.run(service.run(7, sensor_request()))
    service.db.rollback.assert_called_once()
    service.sessions.finish.assert_not_called()


@pytest.mark.parametrize("exception,code", [
    (InvalidRecordsError("unit invalid"), "invalid_records"),
    (CursorConflictError("unit conflict"), "cursor_conflict"),
    (httpx.ConnectError("secret URL must not be persisted"), "sensor_unavailable"),
    (SQLAlchemyError("unit database failure"), "processing_failed"),
    (RuntimeError("sensitive model failure detail"), "detector_failed"),
])
def test_failure_rolls_back_and_persists_only_safe_error_code(analysis, connection_factory, exception, code):
    service, _, _ = analysis
    service.ingestion.persist.return_value = [connection_factory()]
    service._process = MagicMock(side_effect=exception)
    with pytest.raises(AnalysisRunError) as error:
        asyncio.run(service.run(7, sensor_request()))
    assert error.value.code == code and error.value.session_id == "unit-session"
    assert error.value.__cause__ is exception
    service.db.rollback.assert_called_once()
    service.sessions.finish.assert_called_once_with("unit-session", "failed", code)
    assert service.db.commit.call_count == 2  # Initial session, then safe failure status.


def test_cancellation_is_interrupted_and_propagated(analysis, connection_factory):
    service, _, _ = analysis
    service.ingestion.persist.return_value = [connection_factory()]
    service._process = MagicMock(side_effect=asyncio.CancelledError())
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(service.run(7, sensor_request()))
    service.db.rollback.assert_called_once()
    service.sessions.finish.assert_called_once_with("unit-session", "interrupted", "request_interrupted")
    assert service.db.commit.call_count == 2


def test_sensor_batch_commits_before_requesting_next_batch(analysis, connection_factory, raw_record):
    service, _, session = analysis
    session.source = "sensor"
    service.ingestion.persist.return_value = [connection_factory()]
    batch = IngestionBatch(records=[raw_record], sensor_url="unit", file_id="a" * 64, file="conn.log")

    async def stream():
        yield batch
        assert service.db.commit.call_count == 2  # Session and first batch committed.
        yield batch
        assert service.db.commit.call_count == 3

    service.ingestion.batches.side_effect = None
    service.ingestion.batches.return_value = stream()
    result = asyncio.run(service.run(7, AnalysisRequest()))
    assert result["new_connections_ingested"] == 2
    assert result["analysis_session"].records_prepared == 2
    assert service.db.commit.call_count == 4
    assert service.sessions.link.call_args.kwargs == {
        "sensor_url": "unit", "file_id": "a" * 64, "file": "conn.log"}


def test_later_transport_failure_does_not_undo_previous_batch_commit(analysis, connection_factory, raw_record):
    service, _, _ = analysis
    service.ingestion.persist.return_value = [connection_factory()]

    async def stream():
        yield IngestionBatch(records=[raw_record])
        assert service.db.commit.call_count == 2
        raise httpx.ReadTimeout("unit timeout")

    service.ingestion.batches.side_effect = None
    service.ingestion.batches.return_value = stream()
    with pytest.raises(AnalysisRunError) as error:
        asyncio.run(service.run(7, AnalysisRequest()))
    assert error.value.code == "sensor_unavailable"
    assert service.db.commit.call_count == 3
    service.db.rollback.assert_called_once()
    # This asserts transaction ordering, not actual SQLite durability.


def test_invalid_sensor_batch_never_reaches_detector(analysis, raw_record):
    service, detector, _ = analysis

    async def stream():
        yield IngestionBatch(records=[raw_record])

    service.ingestion.batches.side_effect = None
    service.ingestion.batches.return_value = stream()
    service.ingestion.persist.side_effect = ValueError("unit malformed record")
    with pytest.raises(AnalysisRunError) as error:
        asyncio.run(service.run(7, AnalysisRequest()))
    assert error.value.code == "invalid_records"
    detector.analyze_batch.assert_not_called()


def test_empty_sensor_session_completes_with_zero_counts(analysis):
    service, detector, _ = analysis

    async def stream():
        if False:
            yield  # An empty async iterator.

    service.ingestion.batches.side_effect = None
    service.ingestion.batches.return_value = stream()
    result = asyncio.run(service.run(7, AnalysisRequest()))
    assert result["new_connections_ingested"] == result["new_alerts_detected"] == 0
    detector.analyze_batch.assert_not_called()


def test_file_issue_is_committed_and_analysis_continues(analysis, connection_factory, raw_record):
    service, detector, session = analysis
    session.file_issues = []
    issue = SensorFileIssue(file="broken.log.gz", code="corrupt_file", offset=100)
    service.sessions.record_file_issue.side_effect = lambda _, value: session.file_issues.append(value.model_dump())
    service.ingestion.persist.return_value = [connection_factory()]

    async def stream():
        yield IngestionBatch(records=[], issue=issue)
        assert service.db.commit.call_count == 2
        yield IngestionBatch(records=[raw_record])

    service.ingestion.batches.side_effect = None
    service.ingestion.batches.return_value = stream()
    result = asyncio.run(service.run(7, AnalysisRequest()))
    assert result["analysis_session"].status == "completed"
    assert result["analysis_session"].file_issues == [issue]
    service.ingestion.persist.assert_called_once()
    detector.analyze_batch.assert_called_once()
