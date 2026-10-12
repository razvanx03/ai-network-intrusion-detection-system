from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator


class ZeekLogItem(BaseModel):
    """Schema for parsing incoming raw Zeek conn.log JSON objects."""
    uid: str
    ts: float
    src_ip: str = Field(alias="id.orig_h")
    src_port: int = Field(alias="id.orig_p")
    dst_ip: str = Field(alias="id.resp_h")
    dst_port: int = Field(alias="id.resp_p")
    proto: str
    service: Optional[str] = None
    duration: Optional[float] = 0.0
    orig_bytes: Optional[int] = 0
    resp_bytes: Optional[int] = 0
    conn_state: Optional[str] = None
    orig_pkts: Optional[int] = 0
    resp_pkts: Optional[int] = 0
    history: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def normalize_keys_and_values(cls, data: dict):
        if not isinstance(data, dict):
            return data
        
        # Support both 'id.orig_h' (Zeek) and 'src_ip' (internal)
        if "id.orig_h" not in data and "src_ip" in data:
            data["id.orig_h"] = data["src_ip"]
        if "id.orig_p" not in data and "src_port" in data:
            data["id.orig_p"] = data["src_port"]
        if "id.resp_h" not in data and "dst_ip" in data:
            data["id.resp_h"] = data["dst_ip"]
        if "id.resp_p" not in data and "dst_port" in data:
            data["id.resp_p"] = data["dst_port"]

        # Zeek logs often use "-" for null or missing values
        for key in ["duration", "orig_bytes", "resp_bytes", "orig_pkts", "resp_pkts"]:
            if data.get(key) == "-":
                data[key] = 0
        for key in ["service", "conn_state", "history"]:
            if data.get(key) == "-":
                data[key] = None

        return data

    class Config:
        populate_by_name = True


class ConnectionResponse(BaseModel):
    id: int
    uid: str
    ts: float
    src_ip: str
    src_port: int
    dst_ip: str
    dst_port: int
    proto: str
    service: Optional[str] = None
    duration: Optional[float] = 0.0
    orig_bytes: Optional[int] = 0
    resp_bytes: Optional[int] = 0
    conn_state: Optional[str] = None
    orig_pkts: Optional[int] = 0
    resp_pkts: Optional[int] = 0
    history: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ConnectionFilter(BaseModel):
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    proto: Optional[str] = None
    conn_state: Optional[str] = None
    limit: int = 50
    offset: int = 0
