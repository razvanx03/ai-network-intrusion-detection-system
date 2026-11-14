from sqlalchemy.exc import IntegrityError
from app.integrations.sensor_client import sensor_client
from app.repositories.reset_repository import ResetRepository, ResetBusyError
from app.repositories.analysis_repository import AnalysisRepository
from app.services.analysis_service import AnalysisBusyError


class ResetService:
    def __init__(self, db):
        self.db = db
        self.resets = ResetRepository(db)
        self.sessions = AnalysisRepository(db)

    async def run(self, operation_id):
        existing = self.resets.get(operation_id)
        if existing and existing.status == "completed":
            return {"status": "completed"}
        # Do not start destructive work or block analysis on an old/offline collector.
        await sensor_client.require_reset_support()
        try:
            if existing is None:
                self.resets.begin(operation_id)
                if self.sessions.running() is not None:
                    raise AnalysisBusyError("Wait for the running analysis.")
                self.db.commit()
            else:
                self.db.rollback()  # No DB transaction held while contacting the VM.
        except IntegrityError as exc:
            self.db.rollback()
            raise ResetBusyError("A reset is already pending; resume it.") from exc
        except Exception:
            self.db.rollback()
            raise
        # A timeout may hide completed remote deletion: retain the durable guard,
        # and retry this same operation ID. The VM records idempotent receipts.
        await sensor_client.reset_logs(operation_id)
        try:
            self.resets.clear_and_complete(operation_id)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return {"status": "completed"}
