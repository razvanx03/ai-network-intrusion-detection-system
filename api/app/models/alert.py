from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Float, DateTime, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database.base import Base


class Alert(Base):
    __tablename__ = "alerts"

    archive_batch_id: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    analysis_session_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("analysis_sessions.id", ondelete="SET NULL"), index=True, nullable=True,
    )
    provenance: Mapped[str] = mapped_column(
        String(16), default="analysis", server_default="legacy_demo", nullable=False,
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False
    )
    connection_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("connections.id", ondelete="SET NULL"),
        nullable=True
    )
    src_ip: Mapped[str] = mapped_column(String(45), index=True, nullable=False)
    dst_ip: Mapped[str] = mapped_column(String(45), index=True, nullable=False)
    dst_port: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    attack_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(16), index=True, nullable=False)  # LOW, MEDIUM, HIGH, CRITICAL
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    detector: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    mitre_technique: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(
        String(20),
        default="NEW",
        index=True,
        nullable=False
    )  # NEW, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    connection = relationship("Connection", lazy="joined")

    @property
    def proto(self) -> str | None:
        return self.connection.proto if self.connection is not None else None
