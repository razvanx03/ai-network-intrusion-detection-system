from typing import List, Tuple
from sqlalchemy.orm import Session
from app.models.connection import Connection
from app.repositories.connection_repository import ConnectionRepository
from app.schemas.connection import ConnectionFilter


class ConnectionService:
    def __init__(self, db: Session):
        self.db = db
        self.conn_repo = ConnectionRepository(db)

    def get_connections(self, filters: ConnectionFilter) -> Tuple[List[Connection], int]:
        return self.conn_repo.get_filtered(
            src_ip=filters.src_ip,
            dst_ip=filters.dst_ip,
            proto=filters.proto,
            conn_state=filters.conn_state,
            limit=filters.limit,
            offset=filters.offset,
        )

    def count_total(self) -> int:
        return self.conn_repo.count_total()
