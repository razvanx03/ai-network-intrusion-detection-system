
from __future__ import annotations

import gzip
import hashlib
import hmac
import json
import math
import os
import socket
import ssl
import zlib
from pathlib import Path
from typing import Annotated, Any, BinaryIO

import uvicorn
from dotenv import dotenv_values
from fastapi import Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

# Load .env from the same directory as this script.
ENV_FILE = Path(__file__).with_name(".env")
config = {**dotenv_values(ENV_FILE), **os.environ}


def required(name: str) -> str:
    value = config.get(name)
    if value is None or not str(value).strip():
        raise RuntimeError(f"Missing configuration: {name}")
    return str(value).strip()


HOST = required("AGENT_HOST")
PORT = int(required("AGENT_PORT"))
API_KEY = required("API_KEY")
LOG_DIR = Path(required("ZEEK_LOG_DIR")).resolve()
CURRENT_LOG_DIR = (LOG_DIR.parent / "spool" / "zeek").resolve()

MAX_RECORDS = int(config.get("MAX_BATCH_RECORDS", "500"))
MAX_BYTES = int(config.get("MAX_BATCH_BYTES", str(4 * 1024 * 1024)))
MAX_LINE_BYTES = int(config.get("MAX_LINE_BYTES", str(1024 * 1024)))

if len(API_KEY) < 32 or API_KEY.startswith("REPLACE_"):
    raise RuntimeError("Set API_KEY to a random secret of at least 32 characters.")
if not LOG_DIR.is_dir():
    raise RuntimeError(f"Zeek log directory does not exist: {LOG_DIR}")
if not CURRENT_LOG_DIR.is_dir():
    raise RuntimeError(f"Zeek current log directory does not exist: {CURRENT_LOG_DIR}")
if not 1 <= MAX_RECORDS <= 1000:
    raise RuntimeError("MAX_BATCH_RECORDS must be between 1 and 1000.")
if not 1024 <= MAX_BYTES <= 16 * 1024 * 1024:
    raise RuntimeError("MAX_BATCH_BYTES must be between 1 KiB and 16 MiB.")
if not 1024 <= MAX_LINE_BYTES <= MAX_BYTES:
    raise RuntimeError("MAX_LINE_BYTES must be between 1 KiB and MAX_BATCH_BYTES.")

app = FastAPI(title="Zeek Sensor Agent", version="2.6.0")
RESET_SOCKET = Path("/run/nids-reset/control.sock")


class ResetRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    confirmation: Literal["RESET"]


def reset_supported():
    return LOG_DIR == Path("/opt/zeek/logs") and RESET_SOCKET.is_socket()


def authenticate(x_api_key: str | None = Header(default=None)):
    if x_api_key is None or not hmac.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API key.")


@app.get("/reset/capabilities", dependencies=[Depends(authenticate)])
def reset_capabilities():
    return {"supported": reset_supported()}


@app.post("/reset", dependencies=[Depends(authenticate)])
def reset_logs(request: ResetRequest):
    if not reset_supported():
        raise HTTPException(409, detail={"code": "reset_not_supported"})
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as control:
            control.settimeout(300)
            control.connect(str(RESET_SOCKET))
            control.sendall((request.model_dump_json() + "\n").encode())
            response = b""
            while not response.endswith(b"\n"):
                chunk = control.recv(4096)
                if not chunk or len(response) + len(chunk) > 16384:
                    raise ValueError("Invalid reset receipt.")
                response += chunk
        result = json.loads(response)
        if result.get("operation_id") != request.operation_id or result.get("status") != "completed":
            raise ValueError("Reset incomplete.")
        return result
    except (OSError, ValueError) as exc:
        raise HTTPException(503, detail={"code": "reset_sensor_failed"}) from exc


def resolve_log_file(file: str) -> Path:
    relative = Path(file)

    if relative.is_absolute() or ".." in relative.parts:
        raise HTTPException(status_code=400, detail="Invalid log path.")

    if relative.name.split(".", 1)[0] not in ("conn", "dns", "http", "ssl") or not file.endswith((".log", ".log.gz")):
        raise HTTPException(
            status_code=400,
            detail="Only .log and .log.gz files are supported.",
        )

    # Map the virtual "current/" prefix to Zeek's active log directory.
    if relative.parts and relative.parts[0] == "current":
        remaining = Path(*relative.parts[1:])
        candidate = CURRENT_LOG_DIR / remaining
        allowed_root = CURRENT_LOG_DIR
    else:
        candidate = LOG_DIR / relative
        allowed_root = LOG_DIR

    path = candidate.resolve()

    try:
        path.relative_to(allowed_root)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Path outside allowed Zeek log directory.",
        )

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Log file not found.")

    return path


def parse_record(line: bytes) -> dict[str, Any] | None:
    line = line.strip()

    if not line or line.startswith(b"#"):
        return None

    try:
        record = json.loads(line)
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise HTTPException(
            status_code=422,
            detail="Invalid log record. This agent expects Zeek JSON logs.",
        )

    if not isinstance(record, dict):
        raise HTTPException(status_code=422, detail="Expected a JSON object.")

    return record


def open_log(path: Path) -> BinaryIO:
    if path.name.endswith(".gz"):
        return gzip.open(path, "rb")
    return open(path, "rb")


def stream_identity(stream: BinaryIO, sealed: bool = False) -> tuple[str, float] | None:
    """A first-record digest survives Zeek rename and gzip rotation."""
    stream.seek(0)
    while line := stream.readline(MAX_LINE_BYTES + 1):
        if len(line) > MAX_LINE_BYTES:
            raise HTTPException(status_code=413, detail="Log line too large.")
        if not line.endswith(b"\n"):
            if not sealed:
                return None
            # A sealed file can end with valid JSON without a final newline.
        record = parse_record(line)
        if record is not None:
            if "uid" not in record or "ts" not in record:
                raise HTTPException(status_code=422, detail="Expected a UID-linked Zeek record.")
            try:
                first_ts = float(record["ts"])
            except (ValueError, TypeError) as exc:
                raise HTTPException(status_code=422, detail="Invalid connection timestamp.") from exc
            if not math.isfinite(first_ts) or not isinstance(record["uid"], str) or not record["uid"]:
                raise HTTPException(status_code=422, detail="Invalid connection identity.")
            canonical = json.dumps(record, sort_keys=True, separators=(",", ":"))
            return hashlib.sha256(canonical.encode()).hexdigest(), first_ts
    return None


class FileDiscoveryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    excluded_versions: list[Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]] = Field(default_factory=list, max_length=10000)


def file_version(name: str, path: Path) -> str:
    stat = path.stat()
    identity = [name, stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]
    return hashlib.sha256(json.dumps(identity, separators=(",", ":")).encode()).hexdigest()


@app.get("/files", dependencies=[Depends(authenticate)])
def list_files():
    return discover_files()


@app.post("/files/discover", dependencies=[Depends(authenticate)])
def discover_versioned_files(request: FileDiscoveryRequest):
    return discover_files(set(request.excluded_versions), versioned=True)


def discover_files(excluded_versions=(), versioned=False):
    """Discover connection and UID-linked protocol streams, including archives."""
    candidates = []
    for kind in ("conn", "dns", "http", "ssl"):
        candidates.extend(
            (path.relative_to(LOG_DIR).as_posix(), path, True)
            for pattern in (f"{kind}.*.log*", f"{kind}.log", f"{kind}.log.gz")
            for path in LOG_DIR.rglob(pattern)
            if path.name.endswith((".log", ".log.gz"))
            and path.relative_to(LOG_DIR).parts[0] != "current"
        )
        current = CURRENT_LOG_DIR / f"{kind}.log"
        if current.exists():
            candidates.append((f"current/{kind}.log", current, False))
    files = {}
    issues = []
    empty_files = []
    # A bad file must not hide healthy streams during discovery.
    for name, path, archived in sorted(candidates):
        version = None
        issue_count = len(issues)
        try:
            path = resolve_log_file(name)
            if versioned:
                version = file_version(name, path)
                if archived and version in excluded_versions:
                    continue
            with open_log(path) as stream:
                identity = stream_identity(stream, sealed=archived)
            if identity is None:
                if versioned and archived:
                    empty_files.append({"file": name, "fingerprint": version})
                continue
            file_id, first_ts = identity
            kind = path.name.split(".", 1)[0]
            if kind != "conn":
                file_id = hashlib.sha256(f"{kind}:{file_id}".encode()).hexdigest()
            if file_id not in files or archived:
                files[file_id] = {
                    "file": name, "file_id": file_id, "archived": archived, "log_type": kind,
                    "first_ts": first_ts,
                }
                if versioned:
                    files[file_id]["fingerprint"] = version
        except HTTPException as exc:
            if exc.status_code not in (404, 413, 422):
                raise
            code = "file_unavailable" if exc.status_code == 404 else "oversized_file" if exc.status_code == 413 else "corrupt_file"
            issues.append({"file": name, "code": code})
        except (gzip.BadGzipFile, EOFError, zlib.error, ValueError):
            issues.append({"file": name, "code": "corrupt_file"})
        except OSError:
            issues.append({"file": name, "code": "unreadable_file"})
        if versioned and len(issues) > issue_count:
            issues[-1].update({"archived": archived, "fingerprint": version})
    result = {"files": sorted(files.values(), key=lambda item: (item["first_ts"], item["file"])), "issues": issues}
    if versioned:
        result["empty_files"] = empty_files
    return result


@app.get("/health", dependencies=[Depends(authenticate)])
def health():
    return {"status": "ok", "service": "zeek-sensor-agent"}


@app.get("/logs", dependencies=[Depends(authenticate)])
def read_logs(
    file: str = Query(..., description="Relative path, e.g. current/conn.log"),
    offset: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=1000),
    file_id: str | None = Query(None, min_length=64, max_length=64),
    fingerprint: Annotated[str | None, Query(pattern=r"^[a-f0-9]{64}$")] = None,
):
    """Read a batch of JSON Zeek records; the backend owns cursor persistence."""
    if limit > MAX_RECORDS:
        raise HTTPException(
            status_code=400,
            detail=f"limit cannot exceed {MAX_RECORDS}.",
        )

    path = resolve_log_file(file)
    if fingerprint is not None and file_version(file, path) != fingerprint:
        raise HTTPException(status_code=409, detail="Log changed; refresh the file list.")
    records: list[dict[str, Any]] = []
    response_bytes = 0
    has_more = False

    try:
        with open_log(path) as stream:
            archived = not file.startswith("current/")
            identity = stream_identity(stream, sealed=archived)
            actual_id = identity[0] if identity else None
            kind = path.name.split(".", 1)[0]
            if actual_id is not None and kind != "conn":
                actual_id = hashlib.sha256(f"{kind}:{actual_id}".encode()).hexdigest()
            if file_id is not None and actual_id != file_id:
                raise HTTPException(status_code=409, detail="Log rotated; refresh the file list.")
            try:
                stream.seek(offset)
            except (OSError, ValueError):
                raise HTTPException(status_code=416, detail="Invalid offset.")

            if offset:
                stream.seek(offset - 1)
                previous = stream.read(1)
                stream.seek(offset)
                if previous != b"\n":
                    raise HTTPException(
                        status_code=416,
                        detail="Offset must be a line boundary returned by this endpoint.",
                    )

            next_offset = offset

            while True:
                line_start = stream.tell()
                line = stream.readline(MAX_LINE_BYTES + 1)

                if not line:
                    next_offset = stream.tell()
                    break

                if len(line) > MAX_LINE_BYTES:
                    raise HTTPException(status_code=413, detail="Log line too large.")

                # Do not consume a partial line while Zeek is writing it.
                if not line.endswith(b"\n"):
                    if not archived:
                        stream.seek(line_start)
                        next_offset = line_start
                        break

                record = parse_record(line)

                if record is None:
                    next_offset = stream.tell()
                    continue

                record_size = len(
                    json.dumps(record, separators=(",", ":")).encode("utf-8")
                )
                if record_size > MAX_BYTES:
                    raise HTTPException(status_code=413, detail="Record exceeds batch byte limit.")

                if records and response_bytes + record_size > MAX_BYTES:
                    stream.seek(line_start)
                    next_offset = line_start
                    has_more = True
                    break

                if len(records) >= limit:
                    stream.seek(line_start)
                    next_offset = line_start
                    has_more = True
                    break

                records.append(record)
                response_bytes += record_size
                next_offset = stream.tell()

            if not has_more and len(records) >= limit:
                saved_position = stream.tell()

                while True:
                    line = stream.readline(MAX_LINE_BYTES + 1)
                    if not line or (not archived and not line.endswith(b"\n")):
                        break
                    if len(line) > MAX_LINE_BYTES:
                        raise HTTPException(status_code=413, detail="Log line too large.")
                    if parse_record(line) is not None:
                        has_more = True
                        break

                stream.seek(saved_position)

    except HTTPException as exc:
        if exc.status_code in (413, 422):
            code = "oversized_file" if exc.status_code == 413 else "corrupt_file"
            raise HTTPException(status_code=422, detail={"code": code}) from exc
        raise
    except (gzip.BadGzipFile, EOFError, zlib.error, ValueError) as exc:
        raise HTTPException(status_code=422, detail={"code": "corrupt_file"}) from exc
    except OSError as exc:
        raise HTTPException(status_code=422, detail={"code": "unreadable_file"}) from exc

    return {
        "file": file,
        "file_id": actual_id,
        "offset": offset,
        "next_offset": next_offset,
        "records_returned": len(records),
        "has_more": has_more,
        "records": records,
    }


if __name__ == "__main__":
    cert, key = required("TLS_CERT_FILE"), required("TLS_KEY_FILE")
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(cert, key)
    uvicorn.run(app, host=HOST, port=PORT, ssl_certfile=cert, ssl_keyfile=key,
                ssl_version=ssl.PROTOCOL_TLS_SERVER)
