from sqlalchemy import func, insert, or_, select
from app.models.archive_batch import ArchiveRecord
from app.models.connection import Connection
from app.models.alert import Alert
from app.models.analysis_session import AnalysisSession, AnalysisSessionConnection, AlertConnection
from app.models.protocol_event import ProtocolEvent
from app.schemas.alert import AlertResponse
from app.schemas.analysis import AnalysisSessionResponse
from app.schemas.protocol_event import CONTEXT_FIELDS
from app.schemas.connection import ConnectionResponse
from app.repositories.protocol_event_repository import ProtocolEventRepository


class ArchiveSnapshotRepository:
    def __init__(self, db):
        self.db = db

    def _write(self, batch_id, kind, rows):
        buffer = []
        for row in rows:
            buffer.append({"batch_id": batch_id, "kind": kind, "parent_id": None, "member": True,
                           "protocol": None, "flagged": False, **row})
            if len(buffer) == 250:
                self.db.execute(insert(ArchiveRecord), buffer)
                buffer = []
        if buffer:
            self.db.execute(insert(ArchiveRecord), buffer)

    def capture(self, batch):
        """Called inside the locked archive transaction, after marking membership."""
        alert_ids = select(Alert.id).where(Alert.archive_batch_id == batch.id)
        session_ids = select(AnalysisSession.id).where(AnalysisSession.archive_batch_id == batch.id)
        evidence = select(AlertConnection.connection_id).where(AlertConnection.alert_id.in_(alert_ids))
        direct = select(Alert.connection_id).where(Alert.archive_batch_id == batch.id)
        session_connections = select(AnalysisSessionConnection.connection_id).where(AnalysisSessionConnection.session_id.in_(session_ids))
        connections = select(Connection).where(or_(Connection.archive_batch_id == batch.id,
            Connection.id.in_(evidence), Connection.id.in_(direct), Connection.id.in_(session_connections)))
        flagged = set(self.db.scalars(evidence.union(direct)).all())

        def connection_rows():
            # Bounded serialization/context queries even for large traffic batches.
            for chunk in self.db.scalars(connections.order_by(Connection.id).execution_options(yield_per=250)).partitions(250):
                context = ProtocolEventRepository(self.db)
                available = context.available([c.uid for c in chunk])
                names = context.server_names([c.uid for c in chunk])
                for connection in chunk:
                    item = ConnectionResponse.model_validate(connection).model_copy(update={
                        "server_name": names.get(connection.uid),
                        "available_logs": ["conn", *sorted(available.get(connection.uid, []))]})
                    yield dict(record_id=str(item.id), payload=item.model_dump(mode="json"),
                               protocol=item.proto.lower(), flagged=item.id in flagged,
                               member=item.archive_batch_id == batch.id)
        self._write(batch.id, "connection", connection_rows())
        self._write(batch.id, "alert", (
            dict(record_id=str(item.id), parent_id=item.analysis_session_id,
                 payload=AlertResponse.model_validate(item).model_copy(update={"connection": None}).model_dump(mode="json"))
            for item in self.db.scalars(select(Alert).where(Alert.archive_batch_id == batch.id).execution_options(yield_per=250))))
        self._write(batch.id, "session", (
            dict(record_id=item.id, payload=AnalysisSessionResponse.model_validate(item).model_dump(mode="json"))
            for item in self.db.scalars(select(AnalysisSession).where(AnalysisSession.archive_batch_id == batch.id).execution_options(yield_per=250))))
        # Keep evidence and session membership even if live rows later change.
        links = select(AlertConnection.alert_id, AlertConnection.connection_id).where(AlertConnection.alert_id.in_(alert_ids)).union(
            select(Alert.id, Alert.connection_id).where(Alert.archive_batch_id == batch.id, Alert.connection_id.is_not(None)))
        self._write(batch.id, "alert_connection", (
            dict(record_id=f"{aid}:{cid}", parent_id=str(cid), payload={"alert_id": str(aid)}) for aid, cid in self.db.execute(links)))
        self._write(batch.id, "session_connection", (
            dict(record_id=f"{item.session_id}:{item.connection_id}", parent_id=item.session_id,
                 payload={"connection_id": str(item.connection_id), "file": item.file})
            for item in self.db.scalars(select(AnalysisSessionConnection).where(AnalysisSessionConnection.session_id.in_(session_ids)).execution_options(yield_per=250))))
        uids = select(Connection.uid).where(Connection.id.in_(connections.with_only_columns(Connection.id)))
        self._write(batch.id, "event", (
            dict(record_id=item.id, parent_id=item.uid, protocol=item.log_type,
                 payload={"id": item.id, "uid": item.uid, "ts": item.ts, "log_type": item.log_type,
                          "fields": {k: v for k, v in item.fields.items() if k in CONTEXT_FIELDS[item.log_type]}})
            for item in self.db.scalars(select(ProtocolEvent).where(ProtocolEvent.uid.in_(uids)).execution_options(yield_per=250))))
        batch.snapshot_version = 1
        self.db.flush()

    def record(self, batch_id, kind, record_id):
        return self.db.get(ArchiveRecord, (batch_id, kind, str(record_id)))

    def protocols(self, batch_id):
        return list(self.db.scalars(select(ArchiveRecord.protocol).where(
            ArchiveRecord.batch_id == batch_id, ArchiveRecord.kind == "connection", ArchiveRecord.member.is_(True)
        ).distinct().order_by(ArchiveRecord.protocol)).all())

    def page(self, batch_id, kind, limit, offset, protocols=(), alerts_only=False, session_id=None, uid=None, context=None):
        conditions = [ArchiveRecord.batch_id == batch_id, ArchiveRecord.kind == kind]
        if kind == "connection":
            if session_id:
                # Snapshot-only membership: never consult current session links.
                links = select(ArchiveRecord.payload["connection_id"].as_string()).where(
                    ArchiveRecord.batch_id == batch_id, ArchiveRecord.kind == "session_connection", ArchiveRecord.parent_id == session_id)
                conditions.append(ArchiveRecord.record_id.in_(links))
            else:
                conditions.append(ArchiveRecord.member.is_(True))
            if protocols:
                conditions.append(ArchiveRecord.protocol.in_([p.lower() for p in protocols]))
            if alerts_only:
                conditions.append(ArchiveRecord.flagged.is_(True))
        if kind == "event":
            conditions.extend([ArchiveRecord.parent_id == uid, ArchiveRecord.protocol == context])
        if kind == "alert" and uid is not None:
            links = select(ArchiveRecord.payload["alert_id"].as_string()).where(
                ArchiveRecord.batch_id == batch_id, ArchiveRecord.kind == "alert_connection", ArchiveRecord.parent_id == uid)
            conditions.append(ArchiveRecord.record_id.in_(links))
        total = self.db.scalar(select(func.count()).select_from(ArchiveRecord).where(*conditions)) or 0
        if kind in ("connection", "event"):
            time = ArchiveRecord.payload["ts"].as_float()
        else:
            time = ArchiveRecord.payload["started_at" if kind == "session" else "timestamp"].as_string()
        order = time.asc() if kind == "event" else time.desc()
        items = self.db.scalars(select(ArchiveRecord).where(*conditions).order_by(order, ArchiveRecord.record_id).limit(limit).offset(offset)).all()
        payloads = [dict(item.payload) for item in items]
        missing_names = [p for p in payloads if "server_name" not in p]
        if kind == "connection" and missing_names:
            # Older snapshots already retain TLS events; derive only from that frozen copy.
            events = self.db.scalars(select(ArchiveRecord).where(
                ArchiveRecord.batch_id == batch_id, ArchiveRecord.kind == "event",
                ArchiveRecord.protocol == "ssl", ArchiveRecord.parent_id.in_([p["uid"] for p in missing_names])
            ).order_by(ArchiveRecord.payload["ts"].as_float().desc(), ArchiveRecord.record_id.desc()))
            names = {}
            for event in events:
                name = event.payload.get("fields", {}).get("server_name")
                if isinstance(name, str) and name.strip() not in ("", "-"):
                    names.setdefault(event.parent_id, name.strip())
            for payload in missing_names:
                payload["server_name"] = names.get(payload["uid"])
        return dict(items=payloads, total=total, limit=limit, offset=offset)
