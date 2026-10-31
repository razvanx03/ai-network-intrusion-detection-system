import numpy as np
import pandas as pd
from pandas.testing import assert_frame_equal
from pydantic import ValidationError
import pytest

from app.ai.features import COUNTERS, FEATURE_COLUMNS, feature_frame
from app.ai.preparation import prepare_connections
from app.schemas.connection import ZeekLogItem


def test_live_and_raw_normalized_records_produce_identical_features(raw_record, connection_factory):
    raw = ZeekLogItem.model_validate(raw_record)
    prepared = prepare_connections([connection_factory(9)])
    assert prepared[0].connection_id == 9
    assert_frame_equal(feature_frame([raw.model_dump()]),
                       feature_frame([prepared[0].record.model_dump()]))


def test_features_exclude_identifiers_and_preserve_input(raw_record):
    source = pd.DataFrame([raw_record], index=[12])
    original = source.copy(deep=True)
    result = feature_frame(source)
    assert tuple(result.columns) == FEATURE_COLUMNS
    assert list(result.index) == [12]
    assert not {"uid", "ts", "id.orig_h", "id.resp_h"}.intersection(result.columns)
    assert_frame_equal(source, original)
    assert result.loc[12, "log1p_orig_bytes"] == pytest.approx(np.log1p(100))
    assert result.loc[12, "conn_state"] == "sf"


@pytest.mark.parametrize("missing", [None, "-", np.nan])
def test_missing_counter_is_distinguished_from_real_zero(missing, raw_record):
    result = feature_frame([{**raw_record, "orig_bytes": missing}, {**raw_record, "orig_bytes": 0}])
    assert result["log1p_orig_bytes"].tolist() == [0.0, 0.0]
    assert result["missing_orig_bytes"].tolist() == [1.0, 0.0]


@pytest.mark.parametrize("category", [None, "-", "", "   "])
def test_missing_categories_have_explicit_unknown_value(category, raw_record):
    result = feature_frame([{**raw_record, "service": category, "proto": " TCP "}])
    assert result.iloc[0]["service"] == "unknown"
    assert result.iloc[0]["proto"] == "tcp"


@pytest.mark.parametrize("field", COUNTERS)
@pytest.mark.parametrize("value", [-1, float("inf"), float("-inf"), "invalid"])
def test_invalid_counters_fail_instead_of_becoming_benign_zeros(field, value, raw_record):
    with pytest.raises((ValueError, TypeError)):
        feature_frame([{**raw_record, field: value}])


def test_missing_feature_column_fails_fast(raw_record):
    del raw_record["conn_state"]
    with pytest.raises(ValueError, match="conn_state"):
        feature_frame([raw_record])


def test_preparation_rejects_corrupt_stored_record(connection_factory):
    with pytest.raises(ValidationError):
        prepare_connections([connection_factory(duration=-1)])


def test_empty_preparation_is_valid():
    assert prepare_connections([]) == ()
