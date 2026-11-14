from typing import List, Tuple
from sqlalchemy.orm import Session
from app.models.connection import Connection
from app.repositories.connection_repository import ConnectionRepository
from app.schemas.connection import ConnectionFilter
from app.schemas.connection import ConnectionResponse
from app.repositories.protocol_event_repository import ProtocolEventRepository
from fastapi import HTTPException


class ConnectionService:
    def __init__(self, db: Session):
        self.db = db
        self.conn_repo = ConnectionRepository(db)

    def get_connections(self, filters: ConnectionFilter) -> Tuple[List[Connection], int]:
        return self.conn_repo.get_filtered(
            src_ip=filters.src_ip,
            dst_ip=filters.dst_ip,
            conn_state=filters.conn_state,
            limit=filters.limit,
            offset=filters.offset,
            include_archived=filters.include_archived,
            archived_only=filters.archived_only,
            protocols=filters.protocols,
            alerts_only=filters.alerts_only,
        )

    def protocols(self, include_archived: bool = False) -> list[str]:
        return self.conn_repo.protocols(include_archived)

    def count_total(self) -> int:
        return self.conn_repo.count_total()

    def with_context(self, connections):
        available = ProtocolEventRepository(self.db).available([c.uid for c in connections])
        return [ConnectionResponse.model_validate(c).model_copy(update={
            "available_logs": ["conn", *sorted(available.get(c.uid, []))],
        }) for c in connections]

    def events(self, connection_id: int, kind: str, limit: int, offset: int, include_archived: bool = False):
        connection = self.db.get(Connection, connection_id)
        if connection is None or (connection.archive_batch_id is not None and not include_archived):
            raise HTTPException(status_code=404, detail="Connection not found.")
        return ProtocolEventRepository(self.db).page(connection.uid, kind, limit, offset)
