"""Offline feature experiments must retain the live inference boundary."""
import sys
from pathlib import Path

import numpy as np
from pandas.testing import assert_frame_equal
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from ai.study_prepare import DERIVED, HISTORY, enrich, read_zeek
from app.ai.features import FEATURE_COLUMNS, feature_frame


def test_experimental_features_preserve_core_and_do_not_use_labels_or_identifiers(raw_record):
    import pandas as pd
    source = pd.DataFrame([raw_record])
    output = enrich(source)
    assert_frame_equal(output.loc[:, FEATURE_COLUMNS], feature_frame(source))
    changed = source.assign(uid="other", ts=9, label="attack", label_tactic="exfiltration")
    assert_frame_equal(enrich(changed), output)
    assert len(set(HISTORY)) == len(HISTORY)


@pytest.mark.parametrize("duration", [0, None, "-"])
def test_rates_remain_finite_when_duration_is_zero_or_missing(raw_record, duration):
    import pandas as pd
    output = enrich(pd.DataFrame([{**raw_record, "duration": duration,
        "orig_pkts": 0, "resp_pkts": None, "history": "-"}]))
    assert np.isfinite(output.loc[:, list(DERIVED) + list(HISTORY)].to_numpy(dtype=float)).all()
    assert output.history_missing.iloc[0] == 1


def test_history_distinguishes_originator_and_responder_events(raw_record):
    import pandas as pd
    output = enrich(pd.DataFrame([{**raw_record, "history": "S"}, {**raw_record, "history": "s"}]))
    assert output.history_S.tolist() == [1, 0]
    assert output.history_s.tolist() == [0, 1]


def test_zeek_reader_requires_explicit_schema(tmp_path):
    path = tmp_path / "source.tsv"
    path.write_text("unlabelled,text\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Missing Zeek schema"):
        read_zeek(path)


def test_day_partitions_keep_dates_disjoint_and_handle_timestamp_resolution():
    import pandas as pd
    from ai.study_experiment import partitions
    records = []
    for day in pd.date_range("2023-02-20", periods=7, tz="UTC"):
        for label in [0, 1]:
            records.append(dict(day=day.strftime("%Y-%m-%d"), label=label,
                event_time=day.timestamp() + 3600, duration_raw=10, family=str(label)))
    parts, _ = partitions(pd.DataFrame(records), 42, "capture_days")
    assert sum(len(rows) for rows in parts.values()) == len(records)
    assert max(parts["train"].event_time) < min(parts["validation"].event_time)
    assert max(parts["validation"].event_time) < min(parts["test"].event_time)


def test_device_holdout_excludes_shared_endpoint_pairs_from_fitting():
    import pandas as pd
    from ai.study_experiment import partitions
    records = []
    for capture in ["Windows7full-1", "Windows7AD-1", "Echo"]:
        for group in range(100):
            for label in [0, 1]:
                records.append(dict(capture=capture, group=capture + str(group),
                                    label=label, family=str(label)))
    records.append(dict(capture="Windows7full-1", group="Echo0", label=1, family="1"))
    parts, summary = partitions(pd.DataFrame(records), 42, "devices")
    assert summary["purged_shared_pair_rows"] == 1
    for key in ["train", "validation"]:
        assert parts[key].capture.eq("Windows7full-1").all()
        assert set(parts[key].group).isdisjoint(parts["test"].group)
    assert not parts["test"].capture.eq("Windows7full-1").any()
