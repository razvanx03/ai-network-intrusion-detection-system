from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, func, desc
from sqlalchemy.orm import Session
from app.models.alert import Alert
from app.models.analysis_session import AlertConnection
from app.repositories.base_repository import BaseRepository


class AlertRepository(BaseRepository[Alert]):
    def __init__(self, db: Session):
        super().__init__(Alert, db)

    def create_batch(self, alert_dicts: List[dict]) -> List[Alert]:
        if not alert_dicts:
            return []
        objs = [Alert(**a) for a in alert_dicts]
        self.db.add_all(objs)
        self.db.flush()
        for obj in objs:
            self.db.refresh(obj)
        return objs

    def link_connections(self, alert_id: int, connection_ids: list[int]):
        self.db.add_all([AlertConnection(alert_id=alert_id, connection_id=value) for value in connection_ids])

    def get_filtered(
        self,
        severity: Optional[str] = None,
        attack_type: Optional[str] = None,
        status: Optional[str] = None,
        src_ip: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
        provenance: str | None = None,
        include_archived: bool = False,
    ) -> Tuple[List[Alert], int]:
        stmt = select(Alert)
        count_stmt = select(func.count(Alert.id))

        if not include_archived:
            stmt = stmt.where(Alert.archive_batch_id.is_(None))
            count_stmt = count_stmt.where(Alert.archive_batch_id.is_(None))

        if provenance:
            stmt = stmt.where(Alert.provenance == provenance)
            count_stmt = count_stmt.where(Alert.provenance == provenance)

        if severity:
            stmt = stmt.where(Alert.severity == severity.upper())
            count_stmt = count_stmt.where(Alert.severity == severity.upper())
        if attack_type:
            stmt = stmt.where(Alert.attack_type == attack_type)
            count_stmt = count_stmt.where(Alert.attack_type == attack_type)
        if status:
            stmt = stmt.where(Alert.status == status.upper())
            count_stmt = count_stmt.where(Alert.status == status.upper())
        if src_ip:
            stmt = stmt.where(Alert.src_ip == src_ip)
            count_stmt = count_stmt.where(Alert.src_ip == src_ip)

        total = self.db.scalar(count_stmt) or 0
        stmt = stmt.order_by(desc(Alert.timestamp), desc(Alert.id)).offset(offset).limit(limit)
        results = list(self.db.scalars(stmt).all())
        return results, total

    def update_status(self, alert_id: int, new_status: str) -> Optional[Alert]:
        alert = self.get(alert_id)
        if alert and alert.archive_batch_id is None:
            alert.status = new_status.upper()
            self.db.commit()
            self.db.refresh(alert)
        return alert if alert and alert.archive_batch_id is None else None

    def count_total(self) -> int:
        return self.db.scalar(select(func.count(Alert.id)).where(Alert.archive_batch_id.is_(None))) or 0

    def count_legacy(self) -> int:
        return self.db.scalar(select(func.count(Alert.id)).where(Alert.provenance == "legacy_demo", Alert.archive_batch_id.is_(None))) or 0

    def get_stats(self, provenance: str | None = None) -> Dict[str, Any]:
        condition = Alert.archive_batch_id.is_(None)
        if provenance:
            condition = condition & (Alert.provenance == provenance)
        total = self.db.scalar(select(func.count(Alert.id)).where(condition)) or 0
        
        # Severity breakdown
        severities = self.db.execute(
            select(Alert.severity, func.count(Alert.id)).where(condition).group_by(Alert.severity)
        ).all()
        sev_map = {s[0]: s[1] for s in severities}

        # Unresolved count (NEW or ACKNOWLEDGED)
        unresolved = self.db.scalar(
            select(func.count(Alert.id)).where(condition, Alert.status.in_(["NEW", "ACKNOWLEDGED"]))
        ) or 0

        # Top attack types
        top_types_q = self.db.execute(
            select(Alert.attack_type, func.count(Alert.id).label("count"))
            .where(condition)
            .group_by(Alert.attack_type)
            .order_by(desc("count"))
            .limit(5)
        ).all()
        top_attack_types = [{"attack_type": r[0], "count": r[1]} for r in top_types_q]

        # Top attacking IPs
        top_ips_q = self.db.execute(
            select(Alert.src_ip, func.count(Alert.id).label("count"))
            .where(condition)
            .group_by(Alert.src_ip)
            .order_by(desc("count"))
            .limit(5)
        ).all()
        top_attacking_ips = [{"src_ip": r[0], "count": r[1]} for r in top_ips_q]

        return {
            "false_positive_count": self.db.scalar(select(func.count(Alert.id)).where(condition, Alert.status == "FALSE_POSITIVE")) or 0,
            "total_alerts": total,
            "critical_count": sev_map.get("CRITICAL", 0),
            "high_count": sev_map.get("HIGH", 0),
            "medium_count": sev_map.get("MEDIUM", 0),
            "low_count": sev_map.get("LOW", 0),
            "unresolved_count": unresolved,
            "top_attack_types": top_attack_types,
            "top_attacking_ips": top_attacking_ips,
        }

    def get_all_for_export(self, severity: Optional[str] = None, provenance: str | None = None) -> List[Alert]:
        stmt = select(Alert).where(Alert.archive_batch_id.is_(None)).order_by(desc(Alert.timestamp))
        if provenance:
            stmt = stmt.where(Alert.provenance == provenance)
        if severity:
            stmt = stmt.where(Alert.severity == severity.upper())
        return list(self.db.scalars(stmt).all())
