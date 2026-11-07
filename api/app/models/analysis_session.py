from datetime import datetime, timezone
from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class AnalysisSession(Base):
    __tablename__ = "analysis_sessions"
    __table_args__ = (Index(
        "uq_analysis_one_running", "status", unique=True,
        sqlite_where=text("status = 'running'"),
        postgresql_where=text("status = 'running'"),
    ),)

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    requested_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    source: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), index=True, nullable=False)
    detector_status: Mapped[str] = mapped_column(String(32), nullable=False)
    detector_name: Mapped[str] = mapped_column(String(64), nullable=False)
    detector_version: Mapped[str | None] = mapped_column(String(64))
    preparation_version: Mapped[str] = mapped_column(String(64), nullable=False)
    records_received: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_connections_ingested: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_prepared: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_alerts_detected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(32))
    file_issues: Mapped[list[dict]] = mapped_column(JSON, default=list, server_default=text("'[]'"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False,
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AnalysisSessionConnection(Base):
    __tablename__ = "analysis_session_connections"
    session_id: Mapped[str] = mapped_column(
        ForeignKey("analysis_sessions.id", ondelete="CASCADE"), primary_key=True,
    )
    connection_id: Mapped[int] = mapped_column(
        ForeignKey("connections.id", ondelete="CASCADE"), primary_key=True,
    )
    sensor_url: Mapped[str | None] = mapped_column(String(512))
    file_id: Mapped[str | None] = mapped_column(String(64))
    file: Mapped[str | None] = mapped_column(Text)


class AlertConnection(Base):
    __tablename__ = "alert_connections"
    alert_id: Mapped[int] = mapped_column(ForeignKey("alerts.id", ondelete="CASCADE"), primary_key=True)
    connection_id: Mapped[int] = mapped_column(ForeignKey("connections.id", ondelete="CASCADE"), primary_key=True)
