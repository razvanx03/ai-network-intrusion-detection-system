from datetime import datetime, timezone
from typing import Generic, TypeVar
from pydantic import BaseModel, ConfigDict, field_validator

T = TypeVar("T")


class ArchivePage(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


class ArchiveBatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    restored_at: datetime | None
    connections: int
    alerts: int
    sessions: int
    snapshot_version: int | None = None

    @field_validator("created_at", "restored_at")
    @classmethod
    def utc_dates(cls, value):
        return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value
