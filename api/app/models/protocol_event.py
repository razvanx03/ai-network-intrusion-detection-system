from sqlalchemy import Float, JSON, String, Index
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class ProtocolEvent(Base):
    __tablename__ = "protocol_events"
    # No connection FK: protocol records may arrive before conn.log is closed.
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    uid: Mapped[str] = mapped_column(String(64), nullable=False)
    log_type: Mapped[str] = mapped_column(String(8), nullable=False)
    ts: Mapped[float] = mapped_column(Float, nullable=False)
    fields: Mapped[dict] = mapped_column(JSON, nullable=False)
    __table_args__ = (Index("ix_protocol_events_uid_type_ts", "uid", "log_type", "ts"),)
