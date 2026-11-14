from typing import List, Optional, Tuple
from sqlalchemy import select, func, desc
from app.models.alert import Alert
from app.models.analysis_session import AlertConnection
from sqlalchemy.orm import Session
from app.models.connection import Connection
from app.repositories.base_repository import BaseRepository


class ConnectionRepository(BaseRepository[Connection]):
    def __init__(self, db: Session):
        super().__init__(Connection, db)

    def get_by_uid(self, uid: str) -> Optional[Connection]:
        stmt = select(Connection).where(Connection.uid == uid)
        return self.db.scalars(stmt).first()

    def create_batch(self, connection_dicts: List[dict]) -> List[Connection]:
        """Save a batch of connections, skipping duplicate UIDs."""
        if not connection_dicts:
            return []
        
        uids = [c["uid"] for c in connection_dicts if "uid" in c]
        existing_uids = set(
            self.db.scalars(select(Connection.uid).where(Connection.uid.in_(uids))).all()
        )

        new_objs = []
        for c_dict in connection_dicts:
            if c_dict.get("uid") not in existing_uids:
                conn_obj = Connection(**c_dict)
                new_objs.append(conn_obj)
                existing_uids.add(c_dict.get("uid"))

        if new_objs:
            self.db.add_all(new_objs)
            self.db.flush()
            for obj in new_objs:
                self.db.refresh(obj)

        return new_objs

    def get_filtered(
        self,
        src_ip: Optional[str] = None,
        dst_ip: Optional[str] = None,
        conn_state: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        include_archived: bool = False,
        archived_only: bool = False,
        protocols: list[str] | None = None,
        alerts_only: bool = False,
    ) -> Tuple[List[Connection], int]:
        stmt = select(Connection)
        count_stmt = select(func.count(Connection.id))

        if archived_only:
            stmt = stmt.where(Connection.archive_batch_id.is_not(None))
            count_stmt = count_stmt.where(Connection.archive_batch_id.is_not(None))
        elif not include_archived:
            stmt = stmt.where(Connection.archive_batch_id.is_(None))
            count_stmt = count_stmt.where(Connection.archive_batch_id.is_(None))

        if src_ip:
            stmt = stmt.where(Connection.src_ip == src_ip)
            count_stmt = count_stmt.where(Connection.src_ip == src_ip)
        if dst_ip:
            stmt = stmt.where(Connection.dst_ip == dst_ip)
            count_stmt = count_stmt.where(Connection.dst_ip == dst_ip)
        if protocols:
            condition = func.lower(Connection.proto).in_([value.lower() for value in protocols])
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)
        if alerts_only:
            scope = [Alert.provenance == "analysis"]
            if archived_only:
                scope.append(Alert.archive_batch_id.is_not(None))
            elif not include_archived:
                scope.append(Alert.archive_batch_id.is_(None))
            # UNION includes both legacy direct links and linked evidence once,
            # without scanning every alert again for each traffic record.
            sources = select(Alert.connection_id).where(Alert.connection_id.is_not(None), *scope).union(
                select(AlertConnection.connection_id).join(Alert, Alert.id == AlertConnection.alert_id).where(*scope),
            )
            condition = Connection.id.in_(sources)
            stmt = stmt.where(condition)
            count_stmt = count_stmt.where(condition)
        if conn_state:
            stmt = stmt.where(Connection.conn_state == conn_state)
            count_stmt = count_stmt.where(Connection.conn_state == conn_state)

        total = self.db.scalar(count_stmt) or 0
        stmt = stmt.order_by(desc(Connection.ts), desc(Connection.id)).offset(offset).limit(limit)
        results = list(self.db.scalars(stmt).all())
        return results, total

    def protocols(self, include_archived: bool = False) -> list[str]:
        query = select(func.lower(Connection.proto)).distinct().order_by(func.lower(Connection.proto))
        if not include_archived:
            query = query.where(Connection.archive_batch_id.is_(None))
        return list(self.db.scalars(query).all())

    def count_total(self) -> int:
        return self.db.scalar(select(func.count(Connection.id)).where(Connection.archive_batch_id.is_(None))) or 0
