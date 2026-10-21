from typing import Optional, List
from pydantic import BaseModel
from app.schemas.analysis import AnalysisSessionResponse


class SystemHealthResponse(BaseModel):
    status: str
    database: str
    sensor_mode: str
    connections_total: int
    alerts_total: int
    legacy_alerts_total: int
    detector_status: str


class FetchAnalyzeResponse(BaseModel):
    status: str
    message: str
    new_connections_ingested: int
    new_alerts_detected: int
    alerts_summary: dict
    analysis_session: AnalysisSessionResponse


class SensorResetResponse(BaseModel):
    status: str
    message: str
