from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session
from app.core.constants import COOKIE_ACCESS_TOKEN_KEY
from app.core.security import decode_access_token
from app.database.session import get_db
from app.models.user import User
from app.repositories.user_repository import UserRepository


def get_current_user(
    request: Request,
    db: Session = Depends(get_db)
) -> User:
    """Dependency that validates JWT token strictly from HttpOnly cookie."""
    raw_token = request.cookies.get(COOKIE_ACCESS_TOKEN_KEY)

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(raw_token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    username = payload["sub"]
    user_repo = UserRepository(db)
    user = user_repo.get_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    if not user.is_active or not user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Active administrator required.")

    return user
