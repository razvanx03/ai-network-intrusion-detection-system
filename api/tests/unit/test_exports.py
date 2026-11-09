import csv
from datetime import datetime, timezone
import io
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.alert_service import AlertService


def export_service(db, **overrides):
    service = AlertService(db)
    alert = SimpleNamespace(id=1, timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        severity="MEDIUM", attack_type="Suspicious Connection", mitre_technique=None,
        confidence=0.0, src_ip="192.0.2.1", dst_ip="198.51.100.1", dst_port=0,
        detector="unit", status="NEW", description='Review, with "quotes"\nand newline',
        analysis_session_id="unit-session", provenance="analysis")
    for key, value in overrides.items():
        setattr(alert, key, value)
    service.alert_repo = MagicMock()
    service.alert_repo.get_all_for_export.return_value = [alert]
    return service, alert


def test_csv_escapes_multiline_fields_and_preserves_zero_values(db):
    service, alert = export_service(db)
    rows = list(csv.DictReader(io.StringIO(service.export_alerts_csv("analysis"))))
    assert len(rows) == 1
    assert rows[0]["Description"] == alert.description
    assert rows[0]["Confidence"] == "0.00"
    assert rows[0]["Destination Port"] == "0"
    assert rows[0]["Analysis Session"] == "unit-session"
    service.alert_repo.get_all_for_export.assert_called_once_with("analysis")


def test_json_export_retains_provenance_and_nulls(db):
    service, alert = export_service(db, timestamp=None, dst_ip=None, confidence=None)
    result = service.export_alerts_json(provenance="analysis")
    assert result[0]["timestamp"] is None and result[0]["confidence"] is None
    assert result[0]["dst_ip"] is None and result[0]["dst_port"] == 0
    assert result[0]["analysis_session_id"] == "unit-session"
    assert result[0]["description"] == alert.description


def test_empty_exports_have_csv_headers_and_empty_json(db):
    service, _ = export_service(db)
    service.alert_repo.get_all_for_export.return_value = []
    assert list(csv.DictReader(io.StringIO(service.export_alerts_csv()))) == []
    assert "Analysis Session" in service.export_alerts_csv()
    assert service.export_alerts_json() == []
