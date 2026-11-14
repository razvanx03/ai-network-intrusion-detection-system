from app.integrations.sensor_client import sensor_client
from app.repositories.sensor_file_problem_repository import SensorFileProblemRepository
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.reset_repository import ResetRepository
from app.services.analysis_service import AnalysisBusyError


class ProblemNotFoundError(LookupError):
    pass


class ProblemNotBlockedError(ValueError):
    pass


class SensorFileProblemService:
    def __init__(self, db):
        self.db = db
        self.problems = SensorFileProblemRepository(db)

    def page(self, limit, offset):
        return self.problems.page(sensor_client.base_url, limit, offset)

    def retry(self, problem_id):
        try:
            problem = self.problems.lock(sensor_client.base_url, problem_id)
            if problem is None:
                raise ProblemNotFoundError()
            ResetRepository(self.db).require_idle()
            if AnalysisRepository(self.db).running() is not None:
                raise AnalysisBusyError("Wait for the running analysis.")
            if problem.status not in ("blocked", "retry"):
                raise ProblemNotBlockedError()
            problem.status = "retry"
            self.db.commit()
            return {"status": "retry"}
        except Exception:
            self.db.rollback()
            raise
