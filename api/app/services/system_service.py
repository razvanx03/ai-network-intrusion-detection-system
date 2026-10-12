import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.integrations.sensor_client import sensor_client
from app.ai.detector import detector_engine
from app.repositories.connection_repository import ConnectionRepository
from app.repositories.alert_repository import AlertRepository
from app.schemas.connection import ZeekLogItem

logger = logging.getLogger("nids.system_service")


class SystemService:
    def __init__(self, db: Session):
        self.db = db
        self.conn_repo = ConnectionRepository(db)
        self.alert_repo = AlertRepository(db)

    async def fetch_and_analyze(self) -> Dict[str, Any]:
        """
        Main pipeline:
        1. Fetch unread Zeek logs from sensor (or mock)
        2. Validate & normalize schema
        3. Save new connections to SQLite
        4. Run AI & heuristic detection engine
        5. Save generated alerts to SQLite
        6. Return operation summary
        """
        raw_logs = await sensor_client.fetch_new_logs()
        if not raw_logs:
            return {
                "status": "success",
                "message": "No new logs available from sensor.",
                "new_connections_ingested": 0,
                "new_alerts_detected": 0,
                "alerts_summary": {},
            }

        # 1. Parse and validate logs (fail fast on malformed entries)
        validated_connections = [
            ZeekLogItem.model_validate(raw).model_dump()
            for raw in raw_logs
        ]

        # 2. Persist connections
        created_conns = self.conn_repo.create_batch(validated_connections)

        # 3. Analyze through AI & Heuristics engine
        detected_alerts = detector_engine.analyze_batch(validated_connections)

        # 4. Persist alerts
        created_alerts = self.alert_repo.create_batch(detected_alerts)

        severity_summary = {}
        for a in created_alerts:
            severity_summary[a.severity] = severity_summary.get(a.severity, 0) + 1

        return {
            "status": "success",
            "message": f"Successfully ingested {len(created_conns)} new connections and generated {len(created_alerts)} alerts.",
            "new_connections_ingested": len(created_conns),
            "new_alerts_detected": len(created_alerts),
            "alerts_summary": severity_summary,
        }

    async def reset_sensor(self) -> Dict[str, str]:
        """Reset logs on the remote sensor or reset mock generator."""
        await sensor_client.reset_sensor_logs()
        return {
            "status": "success",
            "message": "Sensor logs successfully reset.",
        }

    def clear_database_all(self) -> Dict[str, Any]:
        """Reset local database tables for a fresh demo run."""
        del_alerts = self.alert_repo.delete_all()
        del_conns = self.conn_repo.delete_all()
        return {
            "status": "success",
            "message": f"Cleared {del_conns} connections and {del_alerts} alerts from local database.",
            "deleted_connections": del_conns,
            "deleted_alerts": del_alerts,
        }
