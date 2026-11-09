from datetime import datetime, timezone
from sqlalchemy import desc, func, select, update
from sqlalchemy.orm import Session
from app.models.analysis_session import AnalysisSession, AnalysisSessionConnection, AlertConnection
from app.models.alert import Alert
from app.models.connection import Connection


class AnalysisRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, session_id: str) -> AnalysisSession | None:
        return self.db.get(AnalysisSession, session_id)

    def running(self) -> AnalysisSession | None:
        return self.db.scalar(select(AnalysisSession).where(AnalysisSession.status == "running"))

    def add(self, **values) -> AnalysisSession:
        session = AnalysisSession(**values)
        self.db.add(session)
        self.db.flush()
        return session

    def page(self, limit: int, offset: int, include_archived: bool = False, archived_only: bool = False):
        condition = (AnalysisSession.archive_batch_id.is_not(None) if archived_only
                     else True if include_archived else AnalysisSession.archive_batch_id.is_(None))
        total = self.db.scalar(select(func.count()).select_from(AnalysisSession).where(condition)) or 0
        items = self.db.scalars(select(AnalysisSession).where(condition).order_by(
            desc(AnalysisSession.started_at), desc(AnalysisSession.id),
        ).offset(offset).limit(limit)).all()
        return {"items": list(items), "total": total, "limit": limit, "offset": offset}

    def link(self, session_id: str, connections: list[Connection],
             sensor_url: str | None = None, file_id: str | None = None, file: str | None = None):
        self.db.add_all([
            AnalysisSessionConnection(session_id=session_id, connection_id=connection.id,
                                      sensor_url=sensor_url, file_id=file_id, file=file)
            for connection in connections
        ])

    def connection_page(self, session_id: str, limit: int, offset: int):
        relation = AnalysisSessionConnection
        count = self.db.scalar(select(func.count()).select_from(relation).where(
            relation.session_id == session_id,
        )) or 0
        rows = self.db.execute(select(Connection, relation).join(
            relation, relation.connection_id == Connection.id,
        ).where(relation.session_id == session_id).order_by(Connection.id).offset(offset).limit(limit)).all()
        return rows, count

    def alert_page(self, session_id: str, limit: int, offset: int):
        condition = Alert.analysis_session_id == session_id
        total = self.db.scalar(select(func.count()).select_from(Alert).where(condition)) or 0
        items = self.db.scalars(select(Alert).where(condition).order_by(Alert.id).offset(offset).limit(limit)).all()
        return list(items), total

    def alert_connections(self, session_id: str, alert_id: int):
        alert = self.db.scalar(select(Alert).where(Alert.id == alert_id, Alert.analysis_session_id == session_id))
        if alert is None:
            return None
        query = select(Connection).join(AlertConnection, AlertConnection.connection_id == Connection.id).where(AlertConnection.alert_id == alert_id)
        return list(self.db.scalars(query.order_by(Connection.id)).all())

    def finish(self, session_id: str, status: str, error_code: str | None = None):
        session = self.get(session_id)
        session.status = status
        session.error_code = error_code
        session.finished_at = datetime.now(timezone.utc)

    def record_batch(self, session_id: str, received: int, imported: int, prepared: int, alerts: int):
        session = self.get(session_id)
        session.records_received += received
        session.new_connections_ingested += imported
        session.records_prepared += prepared
        session.new_alerts_detected += alerts

    def record_file_issue(self, session_id: str, issue):
        session = self.get(session_id)
        session.file_issues = [*session.file_issues, issue.model_dump()]

    def interrupt_running(self):
        self.db.execute(update(AnalysisSession).where(AnalysisSession.status == "running").values(
            status="interrupted", error_code="server_restarted", finished_at=datetime.now(timezone.utc),
        ))
