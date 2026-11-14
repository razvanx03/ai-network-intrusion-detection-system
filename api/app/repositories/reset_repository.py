from datetime import datetime, timezone
from sqlalchemy import delete, select, update
from app.models.system_reset import SystemReset
from app.models.archive_batch import ArchiveBatch, ArchiveRecord
from app.models.analysis_session import AnalysisSession, AnalysisSessionConnection, AlertConnection
from app.models.alert import Alert
from app.models.connection import Connection
from app.models.protocol_event import ProtocolEvent
from app.models.sensor_cursor import SensorCursor


class ResetBusyError(RuntimeError):
    pass


class ResetRepository:
    def __init__(self, db):
        self.db = db

    def running(self):
        return self.db.scalar(select(SystemReset).where(SystemReset.status == "running"))

    def require_idle(self):
        if self.running() is not None:
            raise ResetBusyError("A data reset is pending.")

    def get(self, operation_id):
        return self.db.get(SystemReset, operation_id)

    def begin(self, operation_id):
        item = SystemReset(id=operation_id, status="running")
        self.db.add(item)
        self.db.flush()  # Single running-reset index + write lock before analysis check.
        return item

    def clear_and_complete(self, operation_id):
        # Acquire the write lock and recheck idempotency before touching any data.
        changed = self.db.execute(update(SystemReset).where(
            SystemReset.id == operation_id, SystemReset.status == "running"
        ).values(status="completed", completed_at=datetime.now(timezone.utc)))
        if not changed.rowcount:
            return
        for model in (ArchiveRecord, AlertConnection, AnalysisSessionConnection, Alert,
                      ProtocolEvent, Connection, AnalysisSession, ArchiveBatch, SensorCursor):
            self.db.execute(delete(model))
