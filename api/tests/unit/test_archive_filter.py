import pytest
from app.repositories.connection_repository import ConnectionRepository
from app.repositories.alert_repository import AlertRepository
from app.repositories.analysis_repository import AnalysisRepository


@pytest.mark.parametrize("repository", [ConnectionRepository, AlertRepository, AnalysisRepository])
@pytest.mark.parametrize("include_archived,archived_only,expected", [
    (False, False, "IS NULL"), (True, False, None),
    (True, True, "IS NOT NULL"), (False, True, "IS NOT NULL"),
])
def test_archive_filter_applies_to_both_rows_and_pagination_count(db, repository, include_archived, archived_only, expected):
    db.scalar.return_value = 0
    db.scalars.return_value.all.return_value = []
    repo = repository(db)
    if repository is AnalysisRepository:
        repo.page(20, 0, include_archived=include_archived, archived_only=archived_only)
    else:
        repo.get_filtered(limit=20, offset=0, include_archived=include_archived, archived_only=archived_only)
    for statement in (db.scalar.call_args.args[0], db.scalars.call_args.args[0]):
        sql = str(statement)
        if expected is None:
            assert "archive_batch_id IS" not in sql
        else:
            assert f"archive_batch_id {expected}" in sql
