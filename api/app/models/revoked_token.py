from sqlalchemy import Float, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    fingerprint: Mapped[str] = mapped_column(String(64), primary_key=True)
    expires_at: Mapped[float] = mapped_column(Float, nullable=False, index=True)
