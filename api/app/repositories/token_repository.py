from time import time
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from app.models.revoked_token import RevokedToken


class TokenRepository:
    def __init__(self, db):
        self.db = db

    def is_revoked(self, fingerprint: str) -> bool:
        return self.db.get(RevokedToken, fingerprint) is not None

    def revoke(self, fingerprint: str, expires_at: float) -> None:
        if self.is_revoked(fingerprint):
            return
        try:
            self.db.execute(delete(RevokedToken).where(RevokedToken.expires_at <= time()))
            self.db.add(RevokedToken(fingerprint=fingerprint, expires_at=expires_at))
            self.db.commit()
        except IntegrityError:
            self.db.rollback()
            # Concurrent logout of the same token is idempotent.
            if not self.is_revoked(fingerprint):
                raise
        except Exception:
            self.db.rollback()
            raise
