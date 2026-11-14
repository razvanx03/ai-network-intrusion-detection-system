from datetime import datetime, timezone
from sqlalchemy import DateTime, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class SystemReset(Base):
    __tablename__ = "system_resets"
    __table_args__ = (Index("uq_system_reset_running", "status", unique=True,
        sqlite_where=text("status = 'running'"), postgresql_where=text("status = 'running'")),)
    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
