from sqlalchemy import select, func
from sqlalchemy.dialects.sqlite import insert
from app.models.protocol_event import ProtocolEvent


class ProtocolEventRepository:
    def __init__(self, db):
        self.db = db

    def create_batch(self, events: list[dict]):
        for event in events:
            self.db.execute(insert(ProtocolEvent).values(**event).on_conflict_do_nothing(index_elements=["id"]))

    def available(self, uids: list[str]) -> dict[str, list[str]]:
        if not uids:
            return {}
        rows = self.db.execute(select(ProtocolEvent.uid, ProtocolEvent.log_type).where(ProtocolEvent.uid.in_(uids)).distinct())
        result: dict[str, list[str]] = {}
        for uid, kind in rows:
            result.setdefault(uid, []).append(kind)
        return result

    def server_names(self, uids: list[str]) -> dict[str, str]:
        if not uids:
            return {}
        name = ProtocolEvent.fields["server_name"].as_string()
        ranked = select(ProtocolEvent.uid, name.label("name"), func.row_number().over(
            partition_by=ProtocolEvent.uid, order_by=(ProtocolEvent.ts.desc(), ProtocolEvent.id.desc())
        ).label("rank")).where(ProtocolEvent.uid.in_(uids), ProtocolEvent.log_type == "ssl",
                               func.trim(name).not_in(["", "-"])).subquery()
        return {uid: value.strip() for uid, value in self.db.execute(
            select(ranked.c.uid, ranked.c.name).where(ranked.c.rank == 1))}

    def page(self, uid: str, kind: str, limit: int, offset: int):
        condition = (ProtocolEvent.uid == uid, ProtocolEvent.log_type == kind)
        total = self.db.scalar(select(func.count()).select_from(ProtocolEvent).where(*condition)) or 0
        items = self.db.scalars(select(ProtocolEvent).where(*condition).order_by(ProtocolEvent.ts, ProtocolEvent.id).limit(limit).offset(offset)).all()
        return {"items": [{"id": e.id, "uid": e.uid, "log_type": e.log_type, "ts": e.ts, "fields": e.fields} for e in items], "total": total, "limit": limit, "offset": offset}
