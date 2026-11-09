from datetime import date, datetime, timezone
from typing import Optional, List, Literal
from pydantic import BaseModel, Field, StrictInt, field_validator


class AlertResponse(BaseModel):
    archive_batch_id: str | None = None
    id: int
    timestamp: datetime
    connection_id: Optional[int] = None
    proto: str | None = None
    analysis_session_id: Optional[str] = None
    provenance: str
    src_ip: str
    dst_ip: str
    dst_port: Optional[int] = None
    attack_type: str
    severity: str
    confidence: float
    detector: str
    description: str
    mitre_technique: Optional[str] = None
    status: str
    created_at: datetime

    @field_validator("timestamp", "created_at")
    @classmethod
    def utc_dates(cls, value: datetime) -> datetime:
        return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value

    class Config:
        from_attributes = True


class AlertStatusUpdate(BaseModel):
    status: str  # NEW, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE


class AlertBulkStatusUpdate(BaseModel):
    ids: list[StrictInt] = Field(min_length=1, max_length=500)
    status: Literal["NEW", "ACKNOWLEDGED", "RESOLVED", "FALSE_POSITIVE"]

    @field_validator("ids")
    @classmethod
    def positive_unique_ids(cls, values):
        if any(value <= 0 for value in values) or len(values) != len(set(values)):
            raise ValueError("Alert IDs must be positive and unique")
        return values


class AlertFilter(BaseModel):
    include_archived: bool = False
    archived_only: bool = False
    provenance: Literal["analysis"] | None = None
    attack_type: Optional[str] = None
    status: Optional[str] = None
    src_ip: Optional[str] = None
    limit: int = 50
    offset: int = 0


class AlertStatsResponse(BaseModel):
    total_alerts: int
    unresolved_count: int
    top_attack_types: List[dict]


class DailyAlertCount(BaseModel):
    date: date
    count: int


class DailyAlertsResponse(BaseModel):
    period_start: date
    period: Literal["week", "month"]
    today: date
    timezone: str
    days: list[DailyAlertCount]
