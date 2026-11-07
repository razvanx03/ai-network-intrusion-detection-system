"""Manual, request-driven analysis. Per-batch commits preserve ingestion semantics."""
import asyncio
from uuid import uuid4
import httpx
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from app.ai import engine
from app.ai.preparation import PREPARATION_VERSION, prepare_connections
from app.repositories.alert_repository import AlertRepository
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.connection_repository import ConnectionRepository
from app.repositories.sensor_cursor_repository import CursorConflictError
from app.schemas.analysis import AnalysisRequest, AnalysisSessionResponse
from app.services.ingestion_service import IngestionService


class AnalysisBusyError(RuntimeError):
    pass


class StoredSelectionError(ValueError):
    pass


class InvalidRecordsError(ValueError):
    pass


class AnalysisRunError(RuntimeError):
    def __init__(self, session_id: str, code: str):
        self.session_id = session_id
        self.code = code


class AnalysisService:
    def __init__(self, db):
        self.db = db
        self.sessions = AnalysisRepository(db)
        self.connections = ConnectionRepository(db)
        self.alerts = AlertRepository(db)
        self.ingestion = IngestionService(db)

    async def run(self, requested_by: int, request: AnalysisRequest):
        if self.sessions.running() is not None:
            raise AnalysisBusyError("An analysis is already running.")
        detector = engine.analysis_engine
        session_id = uuid4().hex
        try:
            self.sessions.add(
                id=session_id, requested_by=requested_by, source=request.source,
                status="running", detector_status="configured" if detector.configured else "not_configured",
                detector_name=detector.name, detector_version=detector.version,
                preparation_version=PREPARATION_VERSION,
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            if self.sessions.running() is not None:
                raise AnalysisBusyError("An analysis is already running.") from exc
            raise
        phase = "processing_failed"
        summary: dict[str, int] = {}
        try:
            if request.source == "stored":
                connections = self.connections.get_by_ids(request.connection_ids)
                if len(connections) != len(request.connection_ids):
                    raise StoredSelectionError("Selected connections no longer exist.")
                phase = "detector_failed"
                self._process(session_id, connections, len(connections), 0, detector, summary)
                self.db.commit()
            else:
                phase = "sensor_unavailable"
                async for batch in self.ingestion.batches():
                    if batch.issue is not None:
                        self.sessions.record_file_issue(session_id, batch.issue)
                        self.db.commit()
                        continue
                    phase = "invalid_records"
                    connections = self.ingestion.persist(batch)
                    if batch.log_type != "conn":
                        # Context enriches records; it is never input to the selected classifier.
                        self.db.commit()
                        phase = "sensor_unavailable"
                        continue
                    phase = "detector_failed"
                    self._process(session_id, connections, len(batch.records), len(connections),
                                  detector, summary, batch)
                    self.db.commit()
                    phase = "sensor_unavailable"
            self.sessions.finish(session_id, "completed")
            self.db.commit()
        except asyncio.CancelledError:
            self.db.rollback()
            self.sessions.finish(session_id, "interrupted", "request_interrupted")
            self.db.commit()
            raise
        except Exception as exc:
            self.db.rollback()
            code = ("invalid_records" if isinstance(exc, (InvalidRecordsError, StoredSelectionError))
                    else "cursor_conflict" if isinstance(exc, CursorConflictError)
                    else "sensor_unavailable" if isinstance(exc, httpx.HTTPError)
                    else "processing_failed" if isinstance(exc, SQLAlchemyError)
                    else phase)
            self.sessions.finish(session_id, "failed", code)
            self.db.commit()
            # Persist a safe code, never remote response prose, URLs or credentials.
            raise AnalysisRunError(session_id, code) from exc
        session = AnalysisSessionResponse.model_validate(self.sessions.get(session_id))
        return {
            "status": "success", "message": "Analysis session completed.",
            "new_connections_ingested": session.new_connections_ingested,
            "new_alerts_detected": session.new_alerts_detected,
            "alerts_summary": summary, "analysis_session": session,
        }

    def _process(self, session_id, connections, received, imported, detector, summary, batch=None):
        try:
            prepared = prepare_connections(connections)
        except ValidationError as exc:
            raise InvalidRecordsError("Stored source records could not be prepared.") from exc
        findings = [engine.Finding.model_validate(value) for value in detector.analyze_batch(prepared)]
        if not detector.configured and findings:
            raise ValueError("An unconfigured detector cannot generate alerts.")
        by_id = {connection.id: connection for connection in connections}
        self.sessions.link(session_id, connections,
                           sensor_url=batch.sensor_url if batch else None,
                           file_id=batch.file_id if batch else None, file=batch.file if batch else None)
        for finding in findings:
            ids = list(dict.fromkeys(finding.connection_ids))
            if not set(ids).issubset(by_id):
                raise ValueError("Detector findings must reference this batch's source records.")
            source = by_id[ids[0]]
            alert = self.alerts.create_batch([{
                "analysis_session_id": session_id, "provenance": "analysis",
                "connection_id": ids[0] if len(ids) == 1 else None,
                "timestamp": finding.timestamp, "src_ip": source.src_ip,
                "dst_ip": source.dst_ip, "dst_port": source.dst_port,
                "attack_type": finding.attack_type, "severity": finding.severity,
                "confidence": finding.confidence, "detector": detector.name,
                "description": finding.description, "mitre_technique": finding.mitre_technique,
                "status": "NEW",
            }])[0]
            self.alerts.link_connections(alert.id, ids)
            summary[finding.severity] = summary.get(finding.severity, 0) + 1
        self.sessions.record_batch(session_id, received, imported, len(prepared), len(findings))
