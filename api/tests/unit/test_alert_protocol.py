from datetime import datetime, timezone
import pytest
from app.models.alert import Alert
from app.schemas.alert import AlertResponse


@pytest.mark.parametrize("proto", ["tcp", "udp", "icmp", None])
def test_alert_protocol_comes_from_source_record_without_guessing(connection_factory, proto):
    now = datetime.now(timezone.utc)
    alert = Alert(id=1, timestamp=now, created_at=now, provenance="analysis",
                  src_ip="192.0.2.1", dst_ip="198.51.100.1", attack_type="Suspicious Connection",
                  severity="MEDIUM", confidence=0.9, detector="unit", description="unit", status="NEW")
    alert.connection = connection_factory(proto=proto, created_at=now) if proto is not None else None
    assert AlertResponse.model_validate(alert).proto == proto
