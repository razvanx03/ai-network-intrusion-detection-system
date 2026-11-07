from datetime import datetime, timezone
from app.repositories.overview_repository import OverviewRepository
from app.schemas.system import OverviewResponse


def test_last_sync_uses_successful_active_sensor_runs_and_preserves_utc(db):
    completed = datetime(2026, 11, 7, 12, 30)
    db.scalar.side_effect = [0, 0, completed, None]
    db.execute.return_value.all.return_value = []
    result = OverviewRepository(db).summary()
    query = db.scalar.call_args_list[2].args[0]
    assert "max(analysis_sessions.finished_at)" in str(query)
    assert "archive_batch_id IS NULL" in str(query)
    assert {"sensor", "completed", "configured"}.issubset(set(query.compile().params.values()))
    response = OverviewResponse.model_validate(result)
    assert response.last_successful_sync == completed.replace(tzinfo=timezone.utc)
    assert "sessions_total" not in response.model_dump()


def test_no_successful_sensor_run_is_explicitly_absent(db):
    db.scalar.side_effect = [0, 0, None, None]
    db.execute.return_value.all.return_value = []
    assert OverviewResponse.model_validate(OverviewRepository(db).summary()).last_successful_sync is None
