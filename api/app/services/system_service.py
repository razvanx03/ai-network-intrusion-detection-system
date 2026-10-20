import logging
from typing import Dict, Any
from sqlalchemy.orm import Session
from app.integrations.sensor_client import sensor_client
from app.ai.engine import analysis_engine
from app.repositories.connection_repository import ConnectionRepository
from app.repositories.alert_repository import AlertRepository
from app.repositories.sensor_cursor_repository import SensorCursorRepository
from app.schemas.connection import ZeekLogItem

logger = logging.getLogger("nids.system_service")


class SystemService:
    def __init__(self, db: Session):
        self.db = db
        self.conn_repo = ConnectionRepository(db)
        self.alert_repo = AlertRepository(db)
        self.cursor_repo = SensorCursorRepository(db)

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
        if not sensor_client.mock_mode:
            return await self._fetch_remote_files()
        batch = await sensor_client.fetch_new_logs()
        try:
            validated_connections = [
                ZeekLogItem.model_validate(raw).model_dump() for raw in batch.records
            ]
            # Both writes belong to one transaction. Retry only analyzes new UIDs.
            created_conns = self.conn_repo.create_batch(validated_connections)
            new_uids = {connection.uid for connection in created_conns}
            unique_connections = {item["uid"]: item for item in validated_connections}
            detected_alerts = analysis_engine.analyze_batch([
                item for uid, item in unique_connections.items() if uid in new_uids
            ])
            created_alerts = self.alert_repo.create_batch(detected_alerts)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        # Only the local mock generator uses an in-memory batch acknowledgement.
        await sensor_client.acknowledge(batch.batch_id)

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

    async def _fetch_remote_files(self) -> Dict[str, Any]:
        new_connections = 0
        new_alerts = 0
        severity_summary: dict[str, int] = {}
        for file in await sensor_client.list_files():
            cursor = self.cursor_repo.get(sensor_client.base_url, file.file_id)
            if cursor is not None and cursor.completed:
                continue
            offset = cursor.offset if cursor is not None else 0
            # Release the read transaction while waiting for the sensor.
            self.db.rollback()
            while True:
                batch = await sensor_client.read_file(file, offset)
                try:
                    validated = [ZeekLogItem.model_validate(raw).model_dump() for raw in batch.records]
                    # Advance progress and save records/alerts in the SAME transaction.
                    # A failed write leaves this file batch available for a safe retry.
                    self.cursor_repo.advance(
                        sensor_client.base_url, file.file_id, file.file,
                        offset, batch.next_offset, file.archived and not batch.has_more,
                    )
                    connections = self.conn_repo.create_batch(validated)
                    new_uids = {connection.uid for connection in connections}
                    unique = {item["uid"]: item for item in validated}
                    alerts = self.alert_repo.create_batch(analysis_engine.analyze_batch([
                        item for uid, item in unique.items() if uid in new_uids
                    ]))
                    severities = [alert.severity for alert in alerts]
                    self.db.commit()
                except Exception:
                    self.db.rollback()
                    raise
                new_connections += len(connections)
                new_alerts += len(alerts)
                for severity in severities:
                    severity_summary[severity] = severity_summary.get(severity, 0) + 1
                offset = batch.next_offset
                if not batch.has_more:
                    break
        return {
            "status": "success",
            "message": f"Ingested {new_connections} new connections and generated {new_alerts} alerts.",
            "new_connections_ingested": new_connections,
            "new_alerts_detected": new_alerts,
            "alerts_summary": severity_summary,
        }

    async def reset_sensor(self) -> Dict[str, str]:
        """Reset backend-owned file cursors or the mock generator, never log files."""
        if sensor_client.mock_mode:
            await sensor_client.reset_sensor_logs()
        else:
            self.cursor_repo.reset(sensor_client.base_url)
            self.db.commit()
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
