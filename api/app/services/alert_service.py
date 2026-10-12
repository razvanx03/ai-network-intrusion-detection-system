from typing import List, Tuple, Dict, Any, Optional
from sqlalchemy.orm import Session
from app.models.alert import Alert
from app.repositories.alert_repository import AlertRepository
from app.schemas.alert import AlertFilter


class AlertService:
    def __init__(self, db: Session):
        self.db = db
        self.alert_repo = AlertRepository(db)

    def get_alerts(self, filters: AlertFilter) -> Tuple[List[Alert], int]:
        return self.alert_repo.get_filtered(
            severity=filters.severity,
            attack_type=filters.attack_type,
            status=filters.status,
            src_ip=filters.src_ip,
            limit=filters.limit,
            offset=filters.offset,
        )

    def get_stats(self) -> Dict[str, Any]:
        return self.alert_repo.get_stats()

    def update_alert_status(self, alert_id: int, new_status: str) -> Optional[Alert]:
        return self.alert_repo.update_status(alert_id, new_status)
