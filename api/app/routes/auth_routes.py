from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.constants import AUTH_ROUTE_PREFIX, COOKIE_ACCESS_TOKEN_KEY
from app.database.session import get_db
from app.models.user import User
from app.routes.deps import get_current_user
from app.schemas.user import LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix=AUTH_ROUTE_PREFIX, tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    """Authenticate admin user and set JWT in HttpOnly secure cookie."""
    auth_service = AuthService(db)
    token_response = auth_service.authenticate_user(login_data)
    if not token_response:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        )

    # Set secure HttpOnly cookie (inaccessible via JavaScript)
    response.set_cookie(
        key=COOKIE_ACCESS_TOKEN_KEY,
        value=token_response.access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        expires=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        path="/",
    )

    return token_response


@router.post("/logout")
def logout(response: Response):
    """Clear HttpOnly authentication cookie."""
    response.delete_cookie(
        key=COOKIE_ACCESS_TOKEN_KEY,
        httponly=True,
        samesite=settings.COOKIE_SAMESITE,
        secure=settings.COOKIE_SECURE,
        path="/",
    )
    return {
        "status": "success",
        "message": "Logged out successfully."
    }


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Return profile of currently authenticated user."""
    return current_user
