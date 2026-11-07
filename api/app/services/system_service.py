from typing import Any
from app.repositories.overview_repository import OverviewRepository
from app.integrations.sensor_client import sensor_client
from app.repositories.connection_repository import ConnectionRepository
from app.repositories.alert_repository import AlertRepository
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.sensor_cursor_repository import SensorCursorRepository
from app.schemas.analysis import AnalysisRequest
from app.services.analysis_service import AnalysisBusyError, AnalysisService


class SystemService:
    def __init__(self, db):
        self.db = db
        self.conn_repo = ConnectionRepository(db)
        self.alert_repo = AlertRepository(db)
        self.cursor_repo = SensorCursorRepository(db)
        self.sessions = AnalysisRepository(db)

    def overview(self):
        return OverviewRepository(self.db).summary()

    async def fetch_and_analyze(self, requested_by: int) -> dict[str, Any]:
        return await AnalysisService(self.db).run(requested_by, AnalysisRequest())

    def ensure_idle(self):
        if self.sessions.running() is not None:
            raise AnalysisBusyError("Wait for the running analysis before resetting data.")

    async def reset_sensor(self) -> dict[str, str]:
        self.ensure_idle()
        if sensor_client.mock_mode:
            await sensor_client.reset_sensor_logs()
        else:
            self.cursor_repo.reset(sensor_client.base_url)
            self.db.commit()
        return {"status": "success", "message": "Sensor read cursors reset; log files were not changed."}

    def clear_database_all(self) -> dict[str, Any]:
        self.ensure_idle()
        try:
            self.sessions.delete_history()
            alerts = self.alert_repo.delete_all(commit=False)
            connections = self.conn_repo.delete_all(commit=False)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return {
            "status": "success", "message": "Connections, alerts and analysis history cleared.",
            "deleted_connections": connections, "deleted_alerts": alerts,
        }
