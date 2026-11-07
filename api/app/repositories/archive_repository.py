from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import func, select, update
from app.models.archive_batch import ArchiveBatch
from app.models.connection import Connection
from app.models.alert import Alert
from app.models.analysis_session import AnalysisSession


class ArchiveRepository:
    def __init__(self, db):
        self.db = db

    def create(self):
        batch = ArchiveBatch(id=uuid4().hex, connections=0, alerts=0, sessions=0)
        self.db.add(batch)
        # Acquire the transaction's write lock before checking for running analysis.
        self.db.flush()
        return batch

    def archive(self, batch):
        for model, field in ((Connection, "connections"), (Alert, "alerts"), (AnalysisSession, "sessions")):
            result = self.db.execute(update(model).where(model.archive_batch_id.is_(None)).values(archive_batch_id=batch.id))
            setattr(batch, field, result.rowcount)
        self.db.flush()

    def restore(self, batch_id):
        batch = self.db.get(ArchiveBatch, batch_id)
        if batch is None or batch.restored_at is not None:
            return None
        batch.restored_at = datetime.now(timezone.utc)
        self.db.flush()
        return batch

    def restore_records(self, batch_id):
        for model in (Connection, Alert, AnalysisSession):
            self.db.execute(update(model).where(model.archive_batch_id == batch_id).values(archive_batch_id=None))

    def page(self, limit, offset):
        total = self.db.scalar(select(func.count()).select_from(ArchiveBatch)) or 0
        items = self.db.scalars(select(ArchiveBatch).order_by(ArchiveBatch.created_at.desc(), ArchiveBatch.id.desc()).limit(limit).offset(offset)).all()
        return {"items": list(items), "total": total, "limit": limit, "offset": offset}
