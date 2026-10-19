from datetime import datetime
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: "UserResponse"


class UserResponse(BaseModel):
    id: int
    username: str
    is_active: bool
    is_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


TokenResponse.model_rebuild()


class SessionResponse(BaseModel):
    expires_in_minutes: int
    user: UserResponse
