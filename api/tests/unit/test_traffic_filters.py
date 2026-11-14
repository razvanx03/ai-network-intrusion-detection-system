from datetime import datetime, timezone
from unittest.mock import patch
import pytest
from app.models.alert import Alert
from app.repositories.connection_repository import ConnectionRepository
from app.repositories.analysis_repository import AnalysisRepository
from app.repositories.alert_repository import AlertRepository
from app.services.alert_service import AlertService


@pytest.mark.parametrize("include_archived,archived_only,archive_clause", [
    (False, False, "alerts.archive_batch_id IS NULL"),
    (True, False, None), (True, True, "alerts.archive_batch_id IS NOT NULL"),
])
def test_multiple_protocols_and_alert_membership_filter_both_rows_and_total(db, include_archived, archived_only, archive_clause):
    db.scalar.return_value = 0
    db.scalars.return_value.all.return_value = []
    ConnectionRepository(db).get_filtered(protocols=["tcp", "udp"], alerts_only=True,
                                         include_archived=include_archived, archived_only=archived_only)
    for statement in [db.scalar.call_args.args[0], db.scalars.call_args.args[0]]:
        sql = str(statement)
        assert "connections.id IN (SELECT alerts.connection_id" in sql
        assert "UNION SELECT alert_connections.connection_id" in sql
        assert "UNION ALL" not in sql
        assert ["tcp", "udp"] in statement.compile().params.values()
        assert "analysis" in statement.compile().params.values()
        if archive_clause:
            assert archive_clause in sql


def test_protocol_choices_are_discovered_without_a_fixed_protocol_list(db):
    db.scalars.return_value.all.return_value = ["gre", "icmp", "tcp", "udp"]
    assert ConnectionRepository(db).protocols(True) == ["gre", "icmp", "tcp", "udp"]
    query = str(db.scalars.call_args.args[0])
    assert "DISTINCT" in query and "archive_batch_id IS NULL" not in query
    ConnectionRepository(db).protocols(False)
    assert "archive_batch_id IS NULL" in str(db.scalars.call_args.args[0])


def test_sessions_with_alerts_filter_applies_to_count_and_results(db):
    db.scalar.return_value = 0
    db.scalars.return_value.all.return_value = []
    AnalysisRepository(db).page(100, 0, include_archived=True, alerts_only=True)
    for statement in [db.scalar.call_args.args[0], db.scalars.call_args.args[0]]:
        assert "new_alerts_detected >" in str(statement)


def test_dashboard_alerts_include_real_traffic_and_protocol_context_in_one_batch(db, connection_factory):
    now = datetime.now(timezone.utc)
    connection = connection_factory(1, created_at=now)
    alert = Alert(id=1, connection_id=1, timestamp=now, created_at=now, provenance="analysis",
                  src_ip=connection.src_ip, dst_ip=connection.dst_ip, attack_type="Suspicious Connection",
                  severity="MEDIUM", confidence=0.9, detector="unit", description="unit", status="NEW")
    alert.connection = connection
    with patch("app.services.connection_service.ProtocolEventRepository") as context:
        context.return_value.available.return_value = {connection.uid: ["dns"]}
        result = AlertService(db).serialize_alerts([alert])[0]
        context.return_value.available.assert_called_once_with([connection.uid])
    assert result.connection.orig_pkts == connection.orig_pkts
    assert result.connection.duration == connection.duration
    assert result.connection.src_port == connection.src_port
    assert result.connection.available_logs == ["conn", "dns"]


@pytest.mark.parametrize("protocols", [[], ["TCP"], ["tcp", "udp"], ["not-present"]])
def test_dashboard_protocol_filter_covers_direct_and_linked_evidence_without_changing_totals_scope(db, protocols):
    db.scalar.return_value = 0
    db.scalars.return_value.all.return_value = []
    AlertRepository(db).get_filtered(protocols=protocols, provenance="analysis", limit=20, offset=40)
    rows = db.scalars.call_args.args[0]
    count = db.scalar.call_args.args[0]
    assert str(rows.whereclause) == str(count.whereclause)
    assert "alerts.archive_batch_id IS NULL" in str(rows.whereclause)
    if protocols:
        assert [value.lower() for value in protocols] in rows.compile().params.values()
        assert "alerts.connection_id" in str(rows.whereclause)
        assert "alert_connections.alert_id" in str(rows.whereclause)
    else:
        assert "connections.proto" not in str(rows.whereclause)
