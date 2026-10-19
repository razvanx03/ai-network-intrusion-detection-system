"""On-demand Zeek reader with durable, acknowledged batches."""
import gzip
import hashlib
import hmac
import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import uvicorn
from dotenv import dotenv_values
from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel


@dataclass(frozen=True)
class Config:
    host: str
    port: int
    api_key: str
    log_dir: Path
    state_file: Path
    batch_size: int

    @classmethod
    def load(cls):
        env_file = Path(__file__).with_name(".env")
        if not env_file.is_file():
            raise RuntimeError(f"Missing sensor configuration: {env_file}")
        values = {**dotenv_values(env_file), **os.environ}
        names = ("AGENT_HOST", "AGENT_PORT", "API_KEY", "ZEEK_LOG_DIR", "STATE_FILE", "BATCH_SIZE")
        for name in names:
            if not values.get(name):
                raise RuntimeError(f"Missing sensor configuration: {name}")
        config = cls(values["AGENT_HOST"], int(values["AGENT_PORT"]), values["API_KEY"],
                     Path(values["ZEEK_LOG_DIR"]), Path(values["STATE_FILE"]), int(values["BATCH_SIZE"]))
        if len(config.api_key) < 32 or config.api_key == "nids-sensor-agent-secret-key":
            raise RuntimeError("API_KEY must be a randomly generated secret of at least 32 characters")
        if not 1 <= config.port <= 65535 or not 1 <= config.batch_size <= 1000:
            raise RuntimeError("Invalid AGENT_PORT or BATCH_SIZE (allowed: 1..1000)")
        if not config.log_dir.is_absolute() or not config.state_file.is_absolute():
            raise RuntimeError("ZEEK_LOG_DIR and STATE_FILE must be absolute paths")
        return config


MAX_LINE_BYTES = 1024 * 1024
MAX_BATCH_BYTES = 4 * 1024 * 1024


class Acknowledgement(BaseModel):
    batch_id: str


class Reader:
    def __init__(self, config: Config):
        self.config = config
        if not config.log_dir.is_dir():
            raise RuntimeError(f"Zeek log directory missing: {config.log_dir}")
        config.state_file.parent.mkdir(parents=True, exist_ok=True)
        with self.database() as db:
            db.execute("CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL)")
            db.execute("INSERT OR IGNORE INTO state VALUES (1, ?)",
                       (json.dumps({"cursors": {}, "pending": None, "last_ack": None}),))
            self.load(db)

    @contextmanager
    def database(self):
        db = sqlite3.connect(self.config.state_file, timeout=30)
        try:
            db.execute("PRAGMA synchronous=FULL")
            db.execute("BEGIN IMMEDIATE")
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    @staticmethod
    def load(db):
        state = json.loads(db.execute("SELECT data FROM state WHERE id=1").fetchone()[0])
        if not isinstance(state.get("cursors"), dict):
            raise RuntimeError("Invalid sensor cursor state; restore the state database")
        return state

    @staticmethod
    def save(db, state):
        db.execute("UPDATE state SET data=? WHERE id=1", (json.dumps(state),))

    @staticmethod
    def line(stream):
        line = stream.readline(MAX_LINE_BYTES + 1)
        if len(line) > MAX_LINE_BYTES:
            raise RuntimeError("Zeek record exceeds the 1 MiB line limit")
        return line

    def batch(self):
        with self.database() as db:
            state = self.load(db)
            if state["pending"]:
                return state["pending"]["payload"]
            # Current/ may be a symlink. Include it explicitly and deduplicate paths.
            paths = set(self.config.log_dir.rglob("conn*.log*"))
            paths.update((self.config.log_dir / "current").glob("conn*.log*"))
            paths = {p.resolve() for p in paths if p.is_file() and (p.name.endswith(".log") or p.name.endswith(".log.gz"))}
            if not paths:
                raise RuntimeError("No Zeek conn.log files found; check Zeek and ZEEK_LOG_DIR")
            cursors = dict(state["cursors"])
            records, seen, size = [], set(), 0
            for path in sorted(paths, key=lambda p: (p.stat().st_mtime_ns, str(p))):
                opener = gzip.open if path.suffix == ".gz" else open
                with opener(path, "rb") as stream:
                    headers = []
                    # The first complete data record identifies the stream across rename/compression.
                    while True:
                        first = self.line(stream)
                        if not first or not first.endswith(b"\n"):
                            break
                        if first.startswith(b"#fields\t"):
                            headers = first.decode("utf-8").rstrip("\r\n").split("\t")[1:]
                        if first.strip() and not first.startswith(b"#"):
                            break
                    if not first or not first.endswith(b"\n") or first.startswith(b"#"):
                        continue
                    identity = hashlib.sha256(first).hexdigest()
                    if identity in seen:
                        continue
                    seen.add(identity)
                    offset = cursors.get(identity, 0)
                    stream.seek(0, 2)
                    if stream.tell() < offset:
                        raise RuntimeError(f"Zeek file truncated after ingestion: {path}")
                    stream.seek(offset)
                    while len(records) < self.config.batch_size and size < MAX_BATCH_BYTES:
                        start = stream.tell()
                        line = self.line(stream)
                        if not line or not line.endswith(b"\n"):
                            break  # An unfinished final record is retried on the next request.
                        text = line.decode("utf-8").rstrip("\r\n")
                        if text.startswith("#fields\t"):
                            headers = text.split("\t")[1:]
                        elif text and not text.startswith("#"):
                            if text.startswith("{"):
                                record = json.loads(text)
                                if not isinstance(record, dict):
                                    raise ValueError("Expected a JSON object")
                            else:
                                columns = text.split("\t")
                                if not headers or len(columns) != len(headers):
                                    raise ValueError(f"Malformed Zeek TSV record at {path}:{start}")
                                record = dict(zip(headers, columns))
                            records.append(record)
                            size += len(line)
                        cursors[identity] = stream.tell()
                    if len(records) >= self.config.batch_size or size >= MAX_BATCH_BYTES:
                        break
            payload = {"batch_id": str(uuid.uuid4()), "records": records}
            state["pending"] = {"payload": payload, "cursors": cursors}
            self.save(db, state)
            return payload

    def acknowledge(self, batch_id):
        with self.database() as db:
            state = self.load(db)
            if state["last_ack"] == batch_id:
                return
            pending = state["pending"]
            if not pending or pending["payload"]["batch_id"] != batch_id:
                raise HTTPException(409, "Unknown or superseded batch")
            state.update(cursors=pending["cursors"], pending=None, last_ack=batch_id)
            self.save(db, state)

    def reset(self):
        with self.database() as db:
            state = self.load(db)
            if state["pending"]:
                raise HTTPException(409, "A batch is awaiting acknowledgement; finish ingestion before resetting")
            self.save(db, {"cursors": {}, "pending": None, "last_ack": None})


def create_app(config: Config | None = None):
    config = config or Config.load()
    reader = Reader(config)
    app = FastAPI(title="AI NIDS Sensor Agent", docs_url=None, redoc_url=None)

    def authenticate(x_api_key: str | None = Header(default=None)):
        if x_api_key is None or not hmac.compare_digest(x_api_key.encode(), config.api_key.encode()):
            raise HTTPException(401, "Invalid sensor API key")

    @app.get("/health", dependencies=[Depends(authenticate)])
    def health():
        with reader.database() as db:
            state = reader.load(db)
        return {"status": "online", "pending_batch": state["pending"] is not None}

    @app.get("/logs", dependencies=[Depends(authenticate)])
    def logs():
        return reader.batch()

    @app.post("/logs/ack", dependencies=[Depends(authenticate)])
    def acknowledge(body: Acknowledgement):
        reader.acknowledge(body.batch_id)
        return {"status": "acknowledged"}

    @app.delete("/logs", dependencies=[Depends(authenticate)])
    def reset():
        reader.reset()
        return {"status": "cursor_reset"}

    return app


if __name__ == "__main__":
    configuration = Config.load()
    uvicorn.run(create_app(configuration), host=configuration.host, port=configuration.port)
