from sqlalchemy import BigInteger, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class SensorCursor(Base):
    __tablename__ = "sensor_cursors"

    sensor_url: Mapped[str] = mapped_column(String(512), primary_key=True)
    file_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    file: Mapped[str] = mapped_column(String(1024), nullable=False)
    offset: Mapped[int] = mapped_column(BigInteger, nullable=False)
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False)
