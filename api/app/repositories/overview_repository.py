"""Dashboard aggregates over persisted connection and analysis evidence."""
from sqlalchemy import distinct, func, select
from app.models.connection import Connection
from app.models.alert import Alert
from app.models.analysis_session import AnalysisSession, AlertConnection


class OverviewRepository:
    def __init__(self, db):
        self.db = db

    def summary(self) -> dict:
        connections = self.db.scalar(select(func.count(Connection.id)).where(Connection.archive_batch_id.is_(None))) or 0
        flagged = self.db.scalar(select(func.count(distinct(AlertConnection.connection_id))).join(
            Alert, Alert.id == AlertConnection.alert_id,
        ).join(Connection, Connection.id == AlertConnection.connection_id).where(Alert.provenance == "analysis", Alert.archive_batch_id.is_(None), Connection.archive_batch_id.is_(None))) or 0
        protocols = self.db.execute(select(Connection.proto, func.count(Connection.id)).where(Connection.archive_batch_id.is_(None)).group_by(Connection.proto)).all()
        return {
            "connections_total": connections,
            "flagged_connections": flagged,
            "last_successful_sync": self.db.scalar(select(func.max(AnalysisSession.finished_at)).where(
                AnalysisSession.source == "sensor", AnalysisSession.status == "completed",
                AnalysisSession.detector_status == "configured", AnalysisSession.archive_batch_id.is_(None),
            )),
            "running_session_id": self.db.scalar(select(AnalysisSession.id).where(AnalysisSession.status == "running")),
            "protocols": [{"proto": proto, "count": count} for proto, count in protocols],
        }
