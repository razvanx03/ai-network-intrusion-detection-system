"""Audit downloaded sources and prepare identical Zeek connection feature tables."""
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
from app.ai.features import COUNTERS, FEATURE_COLUMNS, feature_frame, FEATURE_VERSION
from ai.acquire import WORK, digest


def pair_groups(a: pd.Series, b: pd.Series) -> pd.Series:
    a, b = a.astype(str), b.astype(str)
    pair = pd.Series(np.where(a < b, a + "|" + b, b + "|" + a), index=a.index)
    # Addresses are split metadata only; never model input or public report content.
    return pd.util.hash_pandas_object(pair, index=False).astype(str)


def prepare(name: str) -> dict:
    tables, audit = [], {"dataset": name, "feature_version": FEATURE_VERSION, "files": []}
    paths = [WORK / "raw/ton/train_test_network.csv"] if name == "ton" else sorted((WORK / "raw/cic").glob("*.parquet"))
    if not paths:
        raise FileNotFoundError(f"No source files found for {name}; run python -m ai.acquire")
    for path in paths:
        raw = pd.read_csv(path, encoding="utf-8-sig", low_memory=False) if name == "ton" else pd.read_parquet(path)
        before = len(raw)
        raw = raw.drop_duplicates().reset_index(drop=True)
        table = raw.rename(columns={"src_bytes": "orig_bytes", "dst_bytes": "resp_bytes",
                                    "src_pkts": "orig_pkts", "dst_pkts": "resp_pkts"})
        features = feature_frame(table)
        family = raw["type"].astype(str).str.lower() if name == "ton" else raw["label"].astype(str).str.lower()
        label = raw["label"].astype(int) if name == "ton" else (~family.eq("benign")).astype(int)
        if not set(label.unique()).issubset({0, 1}):
            raise ValueError(f"Unexpected binary labels in {path.name}")
        source, destination = ("src_ip", "dst_ip") if name == "ton" else ("id.orig_h", "id.resp_h")
        features["group"] = pair_groups(raw[source], raw[destination])
        features["family"] = family
        features["label"] = label
        features["capture"] = path.stem
        features["event_time"] = raw["ts"] if "ts" in raw else np.nan
        features["source_row"] = np.arange(len(raw), dtype=np.int64)
        tables.append(features)
        audit["files"].append({"file": path.name, "sha256": digest(path), "raw_rows": before,
                               "duplicate_rows_removed": before - len(raw), "prepared_rows": len(raw),
                               "families": family.value_counts().to_dict(),
                               "missing_numeric": {name: int(features[f"missing_{name}"].sum()) for name in COUNTERS},
                               "groups": features.group.nunique(),
                               "missed_bytes_nonzero": int((raw["missed_bytes"] > 0).sum()),
                               "label_evidence": raw["evidence"].fillna("none").value_counts().to_dict() if "evidence" in raw else None,
                               "label_confidence": raw["confidence"].fillna("none").value_counts().to_dict() if "confidence" in raw else None})
    prepared = pd.concat(tables, ignore_index=True)
    audit.update(rows=len(prepared), groups=prepared.group.nunique(),
                 families=prepared.family.value_counts().to_dict(),
                 family_groups=prepared.groupby("family").group.nunique().to_dict(),
                 timestamp_available=bool(prepared.event_time.notna().all()),
                 feature_columns=list(FEATURE_COLUMNS))
    (WORK / "prepared").mkdir(exist_ok=True)
    prepared.to_parquet(WORK / f"prepared/{name}.parquet", index=False)
    (WORK / f"prepared/{name}.audit.json").write_text(json.dumps(audit, indent=2), encoding="utf-8")
    print(json.dumps(audit), flush=True)
    return audit


if __name__ == "__main__":
    for dataset in ("ton", "cic"):
        prepare(dataset)
