from app.repositories.archive_repository import ArchiveRepository
from app.repositories.analysis_repository import AnalysisRepository
from app.services.analysis_service import AnalysisBusyError


class EmptyArchiveError(ValueError):
    pass


class ArchiveNotFoundError(ValueError):
    pass


class ArchiveService:
    def __init__(self, db):
        self.db = db
        self.archives = ArchiveRepository(db)
        self.sessions = AnalysisRepository(db)

    def change(self, batch_id=None):
        try:
            batch = self.archives.restore(batch_id) if batch_id else self.archives.create()
            if batch is None:
                raise ArchiveNotFoundError("Archive missing or already restored.")
            if self.sessions.running() is not None:
                raise AnalysisBusyError("Wait for the running analysis.")
            if batch_id:
                self.archives.restore_records(batch_id)
            else:
                self.archives.archive(batch)
                if not (batch.connections or batch.alerts or batch.sessions):
                    raise EmptyArchiveError("No active data to archive.")
            self.db.commit()
            self.db.refresh(batch)
            return batch
        except Exception:
            self.db.rollback()
            raise
