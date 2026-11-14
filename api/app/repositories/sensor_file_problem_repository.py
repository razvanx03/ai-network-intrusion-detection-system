from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import func, select, update
from app.models.sensor_file_problem import SensorFileProblem as Problem


class SensorFileProblemRepository:
    def __init__(self, db):
        self.db = db

    def excluded_versions(self, sensor_url):
        return list(self.db.scalars(select(Problem.fingerprint).where(
            Problem.sensor_url == sensor_url, Problem.status == "blocked")).all())

    def replay_needed(self, sensor_url, file):
        return self.db.scalar(select(Problem.id).where(Problem.sensor_url == sensor_url,
            Problem.file == file, Problem.status.in_(["blocked", "retry"])).limit(1)) is not None

    def record(self, sensor_url, issue, session_id):
        if not issue.archived or not issue.fingerprint or issue.code not in ("corrupt_file", "oversized_file"):
            return True
        existing = self.db.scalar(select(Problem).where(Problem.sensor_url == sensor_url,
            Problem.file == issue.file, Problem.fingerprint == issue.fingerprint))
        if existing is not None and existing.status == "blocked":
            return False
        now = datetime.now(timezone.utc)
        self.db.execute(update(Problem).where(Problem.sensor_url == sensor_url, Problem.file == issue.file,
            Problem.fingerprint != issue.fingerprint, Problem.status.in_(["blocked", "retry"])).values(status="outdated"))
        if existing is None:
            self.db.add(Problem(id=uuid4().hex, sensor_url=sensor_url, file=issue.file,
                fingerprint=issue.fingerprint, code=issue.code, offset=issue.offset, status="blocked",
                attempts=1, first_seen_at=now, last_seen_at=now, first_session_id=session_id, last_session_id=session_id))
        else:
            existing.status = "blocked"
            existing.code = issue.code
            existing.offset = issue.offset
            existing.attempts += 1
            existing.last_seen_at = now
            existing.last_session_id = session_id
        self.db.flush()
        return True

    def resolve(self, sensor_url, file):
        self.db.execute(update(Problem).where(Problem.sensor_url == sensor_url, Problem.file == file,
            Problem.status.in_(["blocked", "retry"])).values(status="resolved"))

    def page(self, sensor_url, limit, offset):
        condition = Problem.sensor_url == sensor_url
        total = self.db.scalar(select(func.count()).select_from(Problem).where(condition)) or 0
        items = self.db.scalars(select(Problem).where(condition).order_by(
            Problem.first_seen_at.desc(), Problem.id.desc()).limit(limit).offset(offset)).all()
        return dict(items=list(items), total=total, limit=limit, offset=offset)

    def lock(self, sensor_url, problem_id):
        self.db.execute(update(Problem).where(Problem.id == problem_id, Problem.sensor_url == sensor_url).values(status=Problem.status))
        return self.db.scalar(select(Problem).where(Problem.id == problem_id, Problem.sensor_url == sensor_url).execution_options(populate_existing=True))
