from unittest.mock import MagicMock

from app.repositories.connection_repository import ConnectionRepository
from app.schemas.connection import ZeekLogItem


def test_ingestion_skips_both_previously_saved_and_repeated_batch_uids(db, raw_record):
    db.scalars.return_value.all.return_value = ["already-saved"]
    values = ZeekLogItem.model_validate(raw_record).model_dump()
    rows = [{**values, "uid": uid} for uid in ["already-saved", "new-1", "new-1", "new-2"]]
    result = ConnectionRepository(db).create_batch(rows)
    assert [connection.uid for connection in result] == ["new-1", "new-2"]
    assert [connection.uid for connection in db.add_all.call_args.args[0]] == ["new-1", "new-2"]
    db.flush.assert_called_once()
    assert db.refresh.call_count == 2
    db.commit.assert_not_called()  # Cursor and findings must share the caller's transaction.


def test_already_ingested_batch_does_not_write_again(db, raw_record):
    db.scalars.return_value.all.return_value = [raw_record["uid"]]
    assert ConnectionRepository(db).create_batch([ZeekLogItem.model_validate(raw_record).model_dump()]) == []
    db.add_all.assert_not_called()
    db.flush.assert_not_called()


def test_empty_batch_does_not_query_database(db):
    assert ConnectionRepository(db).create_batch([]) == []
    db.scalars.assert_not_called()
    db.add_all.assert_not_called()
