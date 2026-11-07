import hashlib
import json
from typing import Literal
from pydantic import BaseModel, Field, JsonValue

LogType = Literal["conn", "dns", "http", "ssl"]
ContextType = Literal["dns", "http", "ssl"]


class ProtocolRecord(BaseModel):
    uid: str = Field(min_length=1, max_length=64)
    ts: float = Field(ge=0, allow_inf_nan=False)


# Explicit fields: exclude credentials, authorization headers and request bodies.
CONTEXT_FIELDS = {
    "dns": {"query", "qclass_name", "qtype_name", "rcode_name", "answers", "TTLs", "rejected", "AA", "TC", "RD", "RA", "trans_id", "rtt"},
    "http": {"method", "host", "uri", "version", "user_agent", "status_code", "status_msg", "request_body_len", "response_body_len", "orig_mime_types", "resp_mime_types", "trans_depth"},
    "ssl": {"server_name", "version", "cipher", "curve", "resumed", "established", "next_protocol", "validation_status", "cert_chain_fps", "client_cert_chain_fps", "subject", "issuer"},
}


def normalize_event(log_type: ContextType, record: dict) -> dict:
    identity = ProtocolRecord.model_validate(record)
    # Hash the complete record so repeated transactions sharing a UID stay distinct.
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False)
    digest = hashlib.sha256(f"{log_type}:{canonical}".encode()).hexdigest()
    fields = {key: value for key, value in record.items() if key in CONTEXT_FIELDS[log_type] and value is not None and value != "-"}
    return {"id": digest, "uid": identity.uid, "ts": identity.ts, "log_type": log_type, "fields": fields}


class ProtocolEventResponse(BaseModel):
    id: str
    uid: str
    log_type: ContextType
    ts: float
    fields: dict[str, JsonValue]
