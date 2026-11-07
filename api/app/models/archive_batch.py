from datetime import datetime, timezone
from sqlalchemy import DateTime, Integer, String
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
