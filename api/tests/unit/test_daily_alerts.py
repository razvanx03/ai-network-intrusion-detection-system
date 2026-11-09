from datetime import date, datetime, timezone
from unittest.mock import MagicMock
import pytest
from app.services.alert_service import AlertService
from app.repositories.alert_repository import AlertRepository


def test_week_contains_seven_days_including_zero_counts(db):
    service = AlertService(db)
    service.alert_repo = MagicMock()
    service.alert_repo.count_daily.return_value = [0, 0, 0, 0, 0, 2174, 0]
    result = service.get_daily_counts(date(2026, 10, 26), "Europe/Bucharest")
    assert len(result["days"]) == 7
    assert result["days"][5] == {"date": date(2026, 10, 31), "count": 2174}
    boundaries = service.alert_repo.count_daily.call_args.args[0]
    assert boundaries[0] == datetime(2026, 10, 25, 22, tzinfo=timezone.utc)
    assert all(day["count"] == 0 for day in result["days"] if day["date"] != date(2026, 10, 31))


@pytest.mark.parametrize("start, hours", [(date(2026, 3, 23), 23), (date(2026, 10, 19), 25)])
def test_daylight_saving_changes_use_actual_local_midnights(db, start, hours):
    service = AlertService(db)
    service.alert_repo = MagicMock()
    service.alert_repo.count_daily.return_value = [0] * 7
    service.get_daily_counts(start, "Europe/Bucharest")
    boundaries = service.alert_repo.count_daily.call_args.args[0]
    assert (boundaries[7] - boundaries[6]).total_seconds() == hours * 3600


@pytest.mark.parametrize("start, zone", [(date(2026, 11, 10), "UTC"), (date(2026, 11, 9), "Not/AZone")])
def test_invalid_week_or_timezone_rejected_before_query(db, start, zone):
    with pytest.raises(ValueError):
        AlertService(db).get_daily_counts(start, zone)
    db.execute.assert_not_called()


def test_daily_query_counts_active_ai_alerts_by_event_time_with_exclusive_end(db):
    boundaries = [datetime(2026, 11, day, tzinfo=timezone.utc) for day in range(9, 17)]
    db.execute.return_value.one.return_value = (0, 1, 0, 5, 0, 0, 0)
    assert AlertRepository(db).count_daily(boundaries) == [0, 1, 0, 5, 0, 0, 0]
    query = db.execute.call_args.args[0]
    sql = str(query)
    assert "archive_batch_id IS NULL" in sql
    assert "alerts.timestamp >=" in sql and "alerts.timestamp <" in sql
    assert "analysis" in query.compile().params.values()
    assert "created_at" not in sql
    db.execute.assert_called_once()


@pytest.mark.parametrize("start, length", [(date(2026, 2, 1), 28), (date(2028, 2, 1), 29),
                                          (date(2026, 4, 1), 30), (date(2026, 12, 1), 31)])
def test_month_covers_every_day_and_next_month_is_excluded(db, start, length):
    service = AlertService(db)
    service.alert_repo = MagicMock()
    service.alert_repo.count_daily.return_value = [0] * length
    result = service.get_daily_counts(start, "UTC", "month")
    assert len(result["days"]) == length
    assert result["period"] == "month"
    assert result["days"][-1]["date"] == start.replace(day=length)
    boundaries = service.alert_repo.count_daily.call_args.args[0]
    assert len(boundaries) == length + 1
    assert boundaries[-1].day == 1
    assert boundaries[-1].month == (start.month % 12) + 1
    assert boundaries[-1].year == start.year + (start.month == 12)


@pytest.mark.parametrize("start, period", [(date(2026, 11, 2), "month"), (date(2026, 11, 1), "year")])
def test_invalid_month_or_period_rejected_before_query(db, start, period):
    with pytest.raises(ValueError):
        AlertService(db).get_daily_counts(start, "UTC", period)
    db.execute.assert_not_called()
