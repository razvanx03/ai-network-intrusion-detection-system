from pydantic import BaseModel, field_validator
from typing import Literal
from datetime import datetime, timezone
from app.schemas.analysis import AnalysisSessionResponse


class SensorStatusResponse(BaseModel):
    status: Literal["available", "unavailable", "host_unreachable", "host_unknown", "unauthorized", "invalid_response", "sample_mode"]
    checked_at: datetime


class SystemHealthResponse(BaseModel):
    status: str
    database: str
    sensor_mode: str
    connections_total: int
    alerts_total: int


class FetchAnalyzeResponse(BaseModel):
    status: str
    message: str
    new_connections_ingested: int
    new_alerts_detected: int
    alerts_summary: dict
    analysis_session: AnalysisSessionResponse




class ProtocolCount(BaseModel):
    proto: str
    count: int


class OverviewResponse(BaseModel):
    connections_total: int
    flagged_connections: int
    last_successful_sync: datetime | None
    running_session_id: str | None
    protocols: list[ProtocolCount]

    @field_validator("last_successful_sync")
    @classmethod
    def sync_utc(cls, value):
        return value.replace(tzinfo=timezone.utc) if value is not None and value.tzinfo is None else value
