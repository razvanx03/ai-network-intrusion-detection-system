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
            provenance=filters.provenance,
            include_archived=filters.include_archived,
        )

    def get_stats(self, provenance: str | None = None) -> Dict[str, Any]:
        return self.alert_repo.get_stats(provenance)

    def update_alert_status(self, alert_id: int, new_status: str) -> Optional[Alert]:
        return self.alert_repo.update_status(alert_id, new_status)

    def export_alerts_csv(self, severity: Optional[str] = None, provenance: str | None = None) -> str:
        import csv
        import io
        alerts = self.alert_repo.get_all_for_export(severity, provenance)
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

    def export_alerts_json(self, severity: Optional[str] = None, provenance: str | None = None) -> List[Dict[str, Any]]:
        alerts = self.alert_repo.get_all_for_export(severity, provenance)
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
