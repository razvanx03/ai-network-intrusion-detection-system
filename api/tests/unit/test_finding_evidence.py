from app.repositories.analysis_repository import AnalysisRepository


def test_finding_evidence_returns_all_linked_records_without_pagination(db, connection_factory):
    db.scalar.return_value = object()
    records = [connection_factory(1), connection_factory(2)]
    db.scalars.return_value.all.return_value = records
    assert AnalysisRepository(db).alert_connections("unit-session", 8) == records
    query = str(db.scalars.call_args.args[0])
    assert "alert_connections.alert_id" in query
    assert "LIMIT" not in query and "OFFSET" not in query
    assert db.scalar.call_count == 1


def test_finding_outside_selected_session_does_not_expose_evidence(db):
    db.scalar.return_value = None
    assert AnalysisRepository(db).alert_connections("unit-session", 8) is None
    query = db.scalar.call_args.args[0]
    assert "unit-session" in query.compile().params.values()
    db.scalars.assert_not_called()
