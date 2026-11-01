"""Bounded CIC follow-up: independently re-extracted Zeek 9 connection inputs.

2018 uses three victim and six client captures, not the complete dataset. The 2019 derivative
is exploratory and has filename/pair-based labels, not verified original truth.
Training is offline; this module never replaces the deployed model.
"""
import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys
import time

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
WORK = ROOT / ".ai-workspace/live-study"

# UTC windows from the primary CNS2022 correction documentation. These are a
# conservative Zeek adaptation, not an import of corrected CICFlowMeter labels.
ATTACKS = {
    "wed": [("18.221.219.4", 21, 1518618806, 1518624631, "ftp_attempted"),
            ("13.58.98.64", 22, 1518631310, 1518636750, "ssh_bruteforce")],
    "thu": [("18.219.211.138", 80, 1518701262, 1518703905, "goldeneye"),
            ("18.217.165.70", 80, 1518706812, 1518709321, "slowloris")],
    "fri": [("13.59.126.31", 21, 1518790334, 1518793513, "ftp_attempted"),
            ("18.219.193.20", 80, 1518803127, 1518803903, "hulk")],
}


def label_2018(raw, capture):
    import pandas as pd
    family = pd.Series("benign", index=raw.index, dtype=str)
    attack_ips = {rule[0] for rules in ATTACKS.values() for rule in rules}
    # Unknown attack-host traffic outside a verified time/target window is
    # excluded, rather than silently called normal.
    family.loc[raw["id.orig_h"].isin(attack_ips) | raw["id.resp_h"].isin(attack_ips)] = "unresolved"
    for source, port, start, end, name in ATTACKS[capture.split("-")[0]]:
        mask = (raw["id.orig_h"].eq(source) & raw["id.resp_h"].eq("172.31.69.25")
                & raw["id.resp_p"].eq(port) & raw.ts.between(start, end))
        family.loc[mask] = name
        if name != "ftp_attempted":
            family.loc[mask & raw.orig_bytes.fillna(0).eq(0)] = "attempted_no_payload"
        if name == "goldeneye":
            family.loc[mask & raw.history.fillna("").str.contains("R", regex=False) & raw.duration.lt(5.05)] = "attempted_early_reset"
            family.loc[mask & raw.history.fillna("").str.contains("r", regex=False)
                & raw.resp_bytes.fillna(0).eq(0) & raw.duration.gt(100)] = "attempted_unresponsive"
    return family


def normalize(raw):
    import pandas as pd
    from app.ai.features import COUNTERS
    for name in (*COUNTERS, "service", "conn_state", "history"):
        if name not in raw:
            raw[name] = None
    for name in COUNTERS:
        raw[name] = pd.to_numeric(raw[name], errors="raise")
    return raw


def prepare(dataset):
    import pandas as pd
    from ai.prepare import pair_groups
    from ai.study_prepare import enrich
    frames, audit = [], {"dataset": dataset, "captures": {}}
    source_directory = WORK / dataset / "zeek-cohort-v2" if dataset == "cic2018" else WORK / dataset
    paths = sorted(source_directory.glob("*.conn.jsonl"))
    if not paths:
        raise FileNotFoundError(f"No extracted {dataset} captures")
    for path in paths:
        capture = path.name.split(".")[0]
        selected, counts = {}, Counter()
        for raw in pd.read_json(path, lines=True, chunksize=30000):
            raw = normalize(raw)
            if dataset == "cic2018":
                tcp = raw.proto.eq("tcp")
                if ((((raw.loc[tcp, "id.orig_p"] // 2)+(raw.loc[tcp, "id.resp_p"] // 2)) % 16) != 0).any():
                    raise ValueError("Capture does not match the reviewed symmetric TCP port cohort")
                raw["family"] = label_2018(raw, capture)
            else:
                # A derivative capture can contain background packets. Positive
                # attribution requires its documented attacker -> victim pair.
                positive = raw["id.orig_h"].eq("172.16.0.5") & raw["id.resp_h"].isin(["192.168.50.1", "192.168.50.4"])
                raw["family"] = capture.lower()
                raw.loc[~positive & (capture != "Benign"), "family"] = "unresolved"
            counts.update(raw.family)
            raw = raw.loc[~raw.family.str.startswith(("attempted", "ftp_attempted", "unresolved"))].copy()
            # Deterministic hash-priority sampling, bounded per capture/family.
            # Metadata hashes are never model inputs. UID is randomized by Zeek,
            # so stable tuples/timestamps are used for reproducible sampling.
            raw["priority"] = pd.util.hash_pandas_object(raw.loc[:, ["ts", "id.orig_h", "id.orig_p", "id.resp_h", "id.resp_p", "proto"]], index=False).to_numpy()
            for family, rows in raw.groupby("family"):
                if family in selected:
                    rows = pd.concat([selected[family], rows], ignore_index=True)
                selected[family] = rows.nsmallest(60000, "priority")
        if not selected:
            raise ValueError(f"No usable labels in {path}")
        raw = pd.concat(selected.values(), ignore_index=True).drop_duplicates(["ts", "id.orig_h", "id.orig_p", "id.resp_h", "id.resp_p", "proto"])
        features = enrich(raw)
        features["family"] = raw.family
        features["label"] = raw.family.ne("benign").astype(int)
        features["capture"] = capture
        features["event_time"] = raw.ts
        features["duration_raw"] = raw.duration.fillna(0)
        features["group"] = pair_groups(raw["id.orig_h"], raw["id.resp_h"])
        features["identity"] = raw.priority.astype(str)
        frames.append(features)
        from ai.live_study import digest
        audit["captures"][capture] = {"raw_label_counts": dict(counts), "retained": len(features),
            "sha256": digest(path), "families": features.family.value_counts().to_dict()}
    frame = pd.concat(frames, ignore_index=True)
    conflicts = frame.groupby("identity").label.nunique()
    conflict_ids = set(conflicts.loc[conflicts.gt(1)].index)
    frame = frame.loc[~frame.identity.isin(conflict_ids)].drop_duplicates("identity")
    audit.update(rows=len(frame), families=frame.family.value_counts().to_dict(), conflicting_identities=len(conflict_ids))
    directory = WORK / "prepared"
    directory.mkdir(exist_ok=True)
    frame.to_parquet(directory / f"{dataset}.parquet", index=False)
    (directory / f"{dataset}.json").write_text(json.dumps(audit, indent=2))
    print(json.dumps(audit), flush=True)


def temporal(frame):
    """Diagnostic only: same campaigns in disjoint time ranges, 60-second purge.

    This explicitly does not assert unseen-host/campaign generalization. A
    separate cross-source/lab transfer evaluates that harder question.
    """
    import pandas as pd
    from ai.experiment import bounded, LIMITS
    pieces = {key: [] for key in LIMITS}
    purged = 0
    for _, rows in frame.groupby(["capture", "family"], sort=True):
        rows = rows.sort_values("event_time")
        if len(rows) < 20:
            purged += len(rows)
            continue
        first, second = rows.event_time.iloc[int(.6*len(rows))], rows.event_time.iloc[int(.8*len(rows))]
        end = rows.event_time + rows.duration_raw
        selections = {"train": end.lt(first-60), "validation": rows.event_time.ge(first) & end.lt(second-60),
            "test": rows.event_time.ge(second)}
        purged += len(rows)-sum(int(mask.sum()) for mask in selections.values())
        for name, mask in selections.items():
            pieces[name].append(rows.loc[mask])
    parts = {name: bounded(pd.concat(rows), LIMITS[name], 42) for name, rows in pieces.items()}
    for name, rows in parts.items():
        if set(rows.label.unique()) != {0, 1}:
            raise ValueError(f"{name} has inadequate class support after temporal purging")
    return parts, purged


def train(dataset, protocol="within_capture_family_time"):
    import joblib
    import numpy as np
    import pandas as pd
    from sklearn.ensemble import IsolationForest
    from sklearn.pipeline import Pipeline
    from threadpoolctl import threadpool_limits
    from ai.experiment import metrics, operating_threshold
    from ai.study_experiment import FEATURE_SETS, classifier
    from ai.live_study import digest
    frame = pd.read_parquet(WORK / f"prepared/{dataset}.parquet")
    spans = frame.groupby(["capture", "family"]).event_time.agg(["min", "max"])
    unsupported = spans.loc[(spans["max"]-spans["min"]).lt(180)]
    if not unsupported.empty:
        raise ValueError(f"Independent temporal calibration is unsupported for these short captures: {list(unsupported.index)}. Use frozen transfer only; do not split adjacent packets into train/test.")
    if protocol == "capture_day":
        if dataset != "cic2018":
            raise ValueError("Whole-day holdout requires independently identified capture dates")
        from ai.experiment import bounded, LIMITS
        parts = {name: bounded(frame.loc[frame.capture.str.startswith(day)].copy(), LIMITS[name], 42)
            for name, day in (("train", "wed"), ("validation", "thu"), ("test", "fri"))}
        purged = 0
        for name, rows in parts.items():
            end = rows.event_time + rows.duration_raw
            day_end = (rows.event_time // 86400 + 1)*86400
            purged += int(end.ge(day_end).sum())
            parts[name] = rows.loc[end.lt(day_end)]
            if set(parts[name].label.unique()) != {0, 1}:
                raise ValueError(f"Capture-day {name} has inadequate class support")
    else:
        parts, purged = temporal(frame)
    suffix = "-capture_day" if protocol == "capture_day" else ""
    models = WORK / "models-v2"
    models.mkdir(exist_ok=True)
    report = {"dataset": dataset, "protocol": protocol,
        "source_sha256": digest(WORK / f"prepared/{dataset}.parquet"), "purged": purged,
        "split": {key: {"rows": len(rows), "families": rows.family.value_counts().to_dict()} for key, rows in parts.items()}, "models": {}}
    for feature_set in ("core", "derived", "history"):
        columns = FEATURE_SETS[feature_set]
        for seed in (42, 43, 44):
            for kind in ("random_forest", "logistic_regression", "isolation_forest"):
                name = f"{dataset}{suffix}-{feature_set}-{kind}-{seed}"
                model = classifier("random_forest" if kind == "isolation_forest" else kind, columns, seed)
                anomaly = kind == "isolation_forest"
                if anomaly:
                    model.set_params(model=IsolationForest(n_estimators=120, max_samples=2048, n_jobs=2, random_state=seed))
                train_rows = parts["train"].loc[parts["train"].label.eq(0)] if anomaly else parts["train"]
                started = time.perf_counter()
                with threadpool_limits(limits=2):
                    model.fit(train_rows.loc[:, columns], None if anomaly else train_rows.label)
                fit_seconds = time.perf_counter()-started
                model.set_params(model__n_jobs=1) if "model__n_jobs" in model.get_params() else None
                def score(rows):
                    with threadpool_limits(limits=1):
                        x = rows.loc[:, columns]
                        return -model.score_samples(x) if anomaly else model.predict_proba(x)[:, 1]
                threshold = operating_threshold(score(parts["validation"]), parts["validation"].label.to_numpy())
                target = models / f"{name}.joblib"
                joblib.dump({"model": model, "kind": kind, "feature_columns": list(columns),
                    "threshold": threshold, "dataset": dataset, "protocol": report["protocol"]}, target, compress=3)
                report["models"][name] = {"sha256": digest(target), "threshold": threshold,
                    "fit_seconds": fit_seconds,
                    "test": metrics(parts["test"], score(parts["test"]), threshold)}
                print(name, report["models"][name]["test"]["confusion_matrix"], flush=True)
                (WORK / f"{dataset}{suffix}-results.json").write_text(json.dumps(report, indent=2))
    pd.concat([rows.assign(partition=name) for name, rows in parts.items()]).to_parquet(WORK / f"prepared/{dataset}{suffix}-partitions.parquet", index=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "train"])
    parser.add_argument("dataset", choices=["cic2018", "cic2019"])
    parser.add_argument("--protocol", choices=["within_capture_family_time", "capture_day"], default="within_capture_family_time")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.dataset)
    else:
        train(args.dataset, args.protocol)


if __name__ == "__main__":
    main()
