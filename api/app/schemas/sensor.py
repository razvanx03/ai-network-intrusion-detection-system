from typing import Literal
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SensorFileIssue(BaseModel):
    file: str = Field(min_length=1, max_length=1024)
    code: Literal["corrupt_file", "unreadable_file", "oversized_file", "file_unavailable"]
    offset: int | None = Field(default=None, ge=0)
    archived: bool = False
    fingerprint: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class SensorFileProblemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    file: str
    code: Literal["corrupt_file", "oversized_file"]
    offset: int | None
    status: Literal["blocked", "retry", "resolved", "outdated"]
    attempts: int
    first_seen_at: datetime
    last_seen_at: datetime
    first_session_id: str
    last_session_id: str

    @field_validator("first_seen_at", "last_seen_at")
    @classmethod
    def utc_dates(cls, value):
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class SensorFileProblemPage(BaseModel):
    items: list[SensorFileProblemResponse]
    total: int
    limit: int
    offset: int
