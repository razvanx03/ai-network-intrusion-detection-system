"""Shared, versioned connection features for offline fitting and live inference."""
from collections.abc import Mapping, Sequence

import numpy as np
import pandas as pd

FEATURE_VERSION = "zeek-conn-core-v1"
COUNTERS = ("duration", "orig_bytes", "resp_bytes", "orig_pkts", "resp_pkts")
CATEGORICAL = ("proto", "service", "conn_state")
NUMERIC = tuple(f"log1p_{name}" for name in COUNTERS) + tuple(f"missing_{name}" for name in COUNTERS)
FEATURE_COLUMNS = NUMERIC + CATEGORICAL


def feature_frame(records: pd.DataFrame | Sequence[Mapping]) -> pd.DataFrame:
    source = records if isinstance(records, pd.DataFrame) else pd.DataFrame.from_records(records)
    missing = set(COUNTERS + CATEGORICAL) - set(source.columns)
    if missing:
        raise ValueError(f"Missing connection feature columns: {sorted(missing)}")
    result = pd.DataFrame(index=source.index)
    for name in COUNTERS:
        raw = source[name].replace("-", np.nan)
        values = pd.to_numeric(raw, errors="raise").astype(float)
        if ((values < 0) | np.isinf(values)).any():
            raise ValueError(f"Invalid nonnegative finite connection feature: {name}")
        result[f"log1p_{name}"] = np.log1p(values.fillna(0))
        result[f"missing_{name}"] = values.isna().astype(float)
    for name in CATEGORICAL:
        values = source[name].astype("string").fillna("unknown").str.strip().str.lower()
        result[name] = values.replace({"-": "unknown", "": "unknown"})
    return result.loc[:, FEATURE_COLUMNS]
