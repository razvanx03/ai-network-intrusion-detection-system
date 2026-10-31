from typing import Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.constants import TOKEN_TYPE_BEARER
from app.core.security import verify_password, create_access_token, decode_access_token, token_fingerprint
from app.repositories.token_repository import TokenRepository
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import LoginRequest, TokenResponse, UserResponse


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def authenticate_user(self, login_data: LoginRequest) -> Optional[TokenResponse]:
        user = self.user_repo.get_by_username(login_data.username)
        if not user or not user.is_active or not user.is_admin:
            return None
        
        if not verify_password(login_data.password, user.hashed_password):
            return None
        
        token = create_access_token(subject=user.username)
        return TokenResponse(
            access_token=token,
            token_type=TOKEN_TYPE_BEARER,
            expires_in_minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES,
            user=UserResponse.model_validate(user),
        )

    def get_user_by_username(self, username: str) -> Optional[User]:
        return self.user_repo.get_by_username(username)

    def revoke_token(self, token: str | None) -> None:
        payload = decode_access_token(token) if token else None
        if payload is not None and "exp" in payload:
            TokenRepository(self.db).revoke(token_fingerprint(token), float(payload["exp"]))
