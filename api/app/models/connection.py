from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, BigInteger, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    uid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    ts: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    src_ip: Mapped[str] = mapped_column(String(45), index=True, nullable=False)
    src_port: Mapped[int] = mapped_column(Integer, nullable=False)
    dst_ip: Mapped[str] = mapped_column(String(45), index=True, nullable=False)
    dst_port: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    proto: Mapped[str] = mapped_column(String(16), nullable=False)
    service: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    duration: Mapped[Optional[float]] = mapped_column(Float, default=None, nullable=True)
    orig_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, default=None, nullable=True)
    resp_bytes: Mapped[Optional[int]] = mapped_column(BigInteger, default=None, nullable=True)
    conn_state: Mapped[Optional[str]] = mapped_column(String(16), index=True, nullable=True)
    orig_pkts: Mapped[Optional[int]] = mapped_column(Integer, default=None, nullable=True)
    resp_pkts: Mapped[Optional[int]] = mapped_column(Integer, default=None, nullable=True)
    history: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
