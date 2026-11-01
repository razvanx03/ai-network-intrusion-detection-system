"""Dashboard aggregates over persisted connection and analysis evidence."""
from sqlalchemy import distinct, func, select
from app.models.connection import Connection
from app.models.alert import Alert
from app.models.analysis_session import AnalysisSession, AnalysisSessionConnection, AlertConnection


class OverviewRepository:
    def __init__(self, db):
        self.db = db

    def summary(self) -> dict:
        analyzed = self.db.scalar(select(func.count(distinct(AnalysisSessionConnection.connection_id))).join(
            AnalysisSession, AnalysisSession.id == AnalysisSessionConnection.session_id,
        ).where(AnalysisSession.detector_status == "configured")) or 0
        connections = self.db.scalar(select(func.count(Connection.id))) or 0
        flagged = self.db.scalar(select(func.count(distinct(AlertConnection.connection_id))).join(
            Alert, Alert.id == AlertConnection.alert_id,
        ).where(Alert.provenance == "analysis")) or 0
        protocols = self.db.execute(select(Connection.proto, func.count(Connection.id)).group_by(Connection.proto)).all()
        statuses = dict(self.db.execute(select(AnalysisSession.status, func.count(AnalysisSession.id)).group_by(AnalysisSession.status)).all())
        return {
            "connections_total": connections, "analyzed_connections": analyzed,
            "pending_connections": max(0, connections - analyzed), "flagged_connections": flagged,
            "sessions_total": sum(statuses.values()), "completed_sessions": statuses.get("completed", 0),
            "failed_sessions": statuses.get("failed", 0) + statuses.get("interrupted", 0),
            "running_session_id": self.db.scalar(select(AnalysisSession.id).where(AnalysisSession.status == "running")),
            "protocols": [{"proto": proto, "count": count} for proto, count in protocols],
        }
