from datetime import datetime, timezone
from sqlalchemy import BigInteger, DateTime, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class SensorFileProblem(Base):
    __tablename__ = "sensor_file_problems"
    __table_args__ = (
        UniqueConstraint("sensor_url", "file", "fingerprint", name="uq_sensor_file_problem_version"),
        Index("ix_sensor_file_problems_scope_status", "sensor_url", "status"),
    )
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    sensor_url: Mapped[str] = mapped_column(String(512), nullable=False)
    file: Mapped[str] = mapped_column(String(1024), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    code: Mapped[str] = mapped_column(String(32), nullable=False)
    offset: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    first_session_id: Mapped[str] = mapped_column(String(32), nullable=False)
    last_session_id: Mapped[str] = mapped_column(String(32), nullable=False)
