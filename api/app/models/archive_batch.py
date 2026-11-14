from datetime import datetime, timezone
from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class ArchiveBatch(Base):
    __tablename__ = "archive_batches"
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    restored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    connections: Mapped[int] = mapped_column(Integer, default=0)
    alerts: Mapped[int] = mapped_column(Integer, default=0)
    sessions: Mapped[int] = mapped_column(Integer, default=0)
    snapshot_version: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ArchiveRecord(Base):
    """Immutable, versioned payloads; intentionally independent of live record FKs."""
    __tablename__ = "archive_records"
    batch_id: Mapped[str] = mapped_column(ForeignKey("archive_batches.id"), primary_key=True)
    kind: Mapped[str] = mapped_column(String(24), primary_key=True)
    record_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    parent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    member: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    protocol: Mapped[str | None] = mapped_column(String(16), nullable=True)
    flagged: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    __table_args__ = (Index("ix_archive_records_parent", "batch_id", "kind", "parent_id"),)
