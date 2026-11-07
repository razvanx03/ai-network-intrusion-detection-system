from datetime import datetime, timezone
from typing import Optional, List, Literal
from pydantic import BaseModel, field_validator


class AlertResponse(BaseModel):
    archive_batch_id: str | None = None
    id: int
    timestamp: datetime
    connection_id: Optional[int] = None
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


class AlertFilter(BaseModel):
    include_archived: bool = False
    provenance: Literal["analysis", "legacy_demo"] | None = None
    severity: Optional[str] = None
    attack_type: Optional[str] = None
    status: Optional[str] = None
    src_ip: Optional[str] = None
    limit: int = 50
    offset: int = 0


class AlertStatsResponse(BaseModel):
    false_positive_count: int
    total_alerts: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    unresolved_count: int
    top_attack_types: List[dict]
    top_attacking_ips: List[dict]
