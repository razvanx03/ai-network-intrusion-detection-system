from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class AlertResponse(BaseModel):
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

    class Config:
        from_attributes = True


class AlertStatusUpdate(BaseModel):
    status: str  # NEW, ACKNOWLEDGED, RESOLVED, FALSE_POSITIVE


class AlertFilter(BaseModel):
    severity: Optional[str] = None
    attack_type: Optional[str] = None
    status: Optional[str] = None
    src_ip: Optional[str] = None
    limit: int = 50
    offset: int = 0


class AlertStatsResponse(BaseModel):
    total_alerts: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    unresolved_count: int
    top_attack_types: List[dict]
    top_attacking_ips: List[dict]
