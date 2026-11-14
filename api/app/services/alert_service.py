from typing import List, Tuple, Dict, Any, Optional
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from sqlalchemy.orm import Session
from app.models.alert import Alert
from app.repositories.alert_repository import AlertRepository
from app.schemas.alert import AlertFilter, AlertBulkStatusUpdate, AlertResponse
from app.services.connection_service import ConnectionService


class AlertService:
    def __init__(self, db: Session):
        self.db = db
        self.alert_repo = AlertRepository(db)

    def get_alerts(self, filters: AlertFilter) -> Tuple[List[Alert], int]:
        return self.alert_repo.get_filtered(
            attack_type=filters.attack_type,
            status=filters.status,
            src_ip=filters.src_ip,
            protocols=filters.protocols,
            limit=filters.limit,
            offset=filters.offset,
            provenance=filters.provenance,
            include_archived=filters.include_archived,
            archived_only=filters.archived_only,
        )

    def get_stats(self, provenance: str | None = None) -> Dict[str, Any]:
        return self.alert_repo.get_stats(provenance)

    def serialize_alerts(self, alerts: list[Alert]) -> list[AlertResponse]:
        sources = [alert.connection for alert in alerts if alert.connection is not None]
        context = {record.id: record for record in ConnectionService(self.db).with_context(sources)}
        return [AlertResponse.model_validate(alert).model_copy(update={
            "connection": context.get(alert.connection_id),
        }) for alert in alerts]

    def get_daily_counts(self, period_start: date, timezone_name: str, period: str = "week"):
        if not 1900 <= period_start.year < 9999:
            raise ValueError("period_start must be between years 1900 and 9998")
        if period not in ("week", "month"):
            raise ValueError("Unknown period")
        if period == "week" and period_start.weekday() != 0:
            raise ValueError("A week must start on Monday")
        if period == "month" and period_start.day != 1:
            raise ValueError("A month must start on its first day")
        try:
            zone = ZoneInfo(timezone_name)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("Unknown timezone") from exc
        if period == "week":
            day_count = 7
        else:
            from calendar import monthrange
            day_count = monthrange(period_start.year, period_start.month)[1]
        dates = [period_start + timedelta(days=index) for index in range(day_count + 1)]
        boundaries = [datetime.combine(day, time.min, zone).astimezone(timezone.utc) for day in dates]
        counts = self.alert_repo.count_daily(boundaries)
        return {"period_start": period_start, "period": period, "timezone": timezone_name,
                "today": datetime.now(zone).date(),
                "days": [{"date": day, "count": count} for day, count in zip(dates, counts)]}

    def update_alert_status(self, alert_id: int, new_status: str) -> Optional[Alert]:
        return self.alert_repo.update_status(alert_id, new_status)

    def update_many_statuses(self, payload: AlertBulkStatusUpdate):
        try:
            updated = self.alert_repo.update_many_statuses(payload.ids, payload.status)
            if set(updated) != set(payload.ids):
                raise LookupError("One or more selected findings are unavailable")
            self.db.commit()
            return {"updated": len(updated)}
        except Exception:
            self.db.rollback()
            raise

    def export_alerts_csv(self, provenance: str | None = None) -> str:
        import csv
        import io
        alerts = self.alert_repo.get_all_for_export(provenance)
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "Timestamp", "Severity", "Attack Type", "MITRE Technique",
            "Confidence", "Source IP", "Destination IP", "Destination Port",
            "Detector", "Status", "Description", "Analysis Session", "Provenance"
        ])
        for a in alerts:
            writer.writerow([
                a.id,
                a.timestamp.isoformat() if a.timestamp else "",
                a.severity,
                a.attack_type,
                a.mitre_technique or "",
                f"{a.confidence:.2f}" if a.confidence is not None else "",
                a.src_ip,
                a.dst_ip or "",
                a.dst_port if a.dst_port is not None else "",
                a.detector or "",
                a.status,
                a.description or "", a.analysis_session_id or "", a.provenance
            ])
        return output.getvalue()

    def export_alerts_json(self, provenance: str | None = None) -> List[Dict[str, Any]]:
        alerts = self.alert_repo.get_all_for_export(provenance)
        return [
            {
                "id": a.id,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
                "severity": a.severity,
                "attack_type": a.attack_type,
                "mitre_technique": a.mitre_technique,
                "confidence": a.confidence,
                "src_ip": a.src_ip,
                "dst_ip": a.dst_ip,
                "dst_port": a.dst_port,
                "detector": a.detector,
                "status": a.status,
                "description": a.description,
                "analysis_session_id": a.analysis_session_id,
                "provenance": a.provenance,
            }
            for a in alerts
        ]
