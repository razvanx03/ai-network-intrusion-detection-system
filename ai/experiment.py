"""Bounded CPU experiments; held-out results never set the operating threshold.

python -m ai.experiment --seeds 42 43 44
"""
import argparse
import json
import os
import platform
import sys
import time
from pathlib import Path

# Bound native BLAS threads before importing numerical libraries.
os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, precision_score, recall_score, f1_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from app.ai.features import FEATURE_COLUMNS, FEATURE_VERSION, NUMERIC, CATEGORICAL
from ai.acquire import WORK, digest

TARGET_FPR = 0.01
LIMITS = {"train": 80000, "validation": 20000, "test": 40000}


def transform() -> ColumnTransformer:
    return ColumnTransformer([("numeric", StandardScaler(), list(NUMERIC)),
                              ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), list(CATEGORICAL))])


def bounded(frame: pd.DataFrame, limit: int, seed: int) -> pd.DataFrame:
    if len(frame) <= limit:
        return frame.copy()
    # Keep each available family, with proportional allocation; never oversample.
    counts = frame.family.value_counts()
    allocation = (counts / len(frame) * limit).astype(int).clip(lower=1)
    while allocation.sum() > limit:
        allocation.loc[allocation.idxmax()] -= 1
    return pd.concat([frame.loc[frame.family.eq(family)].sample(n=int(count), random_state=seed)
                      for family, count in allocation.items()]).sort_index()


def split(frame: pd.DataFrame, seed: int, protocol: str) -> tuple[dict, dict]:
    if protocol == "endpoint_pairs":
        train, test = next(GroupShuffleSplit(n_splits=1, test_size=.2, random_state=seed).split(frame, groups=frame.group))
        subtrain, validation = next(GroupShuffleSplit(n_splits=1, test_size=.25, random_state=seed + 100).split(frame.iloc[train], groups=frame.group.iloc[train]))
        parts = {"train": frame.iloc[train[subtrain]], "validation": frame.iloc[train[validation]], "test": frame.iloc[test]}
        for a, b in (("train", "validation"), ("train", "test"), ("validation", "test")):
            if set(parts[a].group) & set(parts[b].group):
                raise ValueError("Endpoint-pair split overlap")
        purged = 0
    elif protocol == "within_scenario_time":
        # Supplement only: known-campaign evaluation, not independent-campaign evidence.
        pieces = {key: [] for key in LIMITS}
        purged = 0
        for _, rows in frame.groupby("family", sort=True):
            rows = rows.sort_values("event_time")
            if len(rows) < 10:
                purged += len(rows)
                continue
            first = rows.event_time.iloc[int(.6 * len(rows))]
            second = rows.event_time.iloc[int(.8 * len(rows))]
            end = rows.event_time + np.expm1(rows.log1p_duration)
            selections = {"train": end.lt(first - 60),
                          "validation": rows.event_time.ge(first) & end.lt(second - 60),
                          "test": rows.event_time.ge(second)}
            purged += len(rows) - sum(int(mask.sum()) for mask in selections.values())
            for key, mask in selections.items():
                pieces[key].append(rows.loc[mask])
        parts = {key: pd.concat(values) for key, values in pieces.items()}
    else:
        raise ValueError(f"Unsupported protocol: {protocol}")
    summary = {key: {"available": len(value), "families": value.family.value_counts().to_dict(),
                     "benign": int(value.label.eq(0).sum()), "attack": int(value.label.eq(1).sum())}
               for key, value in parts.items()}
    summary["purged_boundary_records"] = purged
    parts = {key: bounded(value, LIMITS[key], seed) for key, value in parts.items()}
    for key, value in parts.items():
        if set(value.label.unique()) != {0, 1}:
            raise ValueError(f"{key} has no two-class support; report as unsupported, do not choose another seed silently")
        summary[key]["used"] = len(value)
        summary[key]["used_families"] = value.family.value_counts().to_dict()
    return parts, summary


def operating_threshold(scores: np.ndarray, labels: np.ndarray) -> float:
    benign = np.asarray(scores)[np.asarray(labels) == 0]
    if len(benign) < 100:
        raise ValueError("At least 100 benign validation records are required for threshold calibration")
    # Strict comparison plus nextafter resolves tied scores conservatively.
    return float(np.nextafter(np.quantile(benign, 1 - TARGET_FPR, method="higher"), np.inf))


def metrics(rows: pd.DataFrame, scores: np.ndarray, threshold: float) -> dict:
    y = rows.label.to_numpy()
    predicted = (np.asarray(scores) >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y, predicted, labels=[0, 1]).ravel()
    return {"rows": len(rows), "attack_prevalence": float(y.mean()),
            "precision": float(precision_score(y, predicted, zero_division=0)),
            "recall": float(recall_score(y, predicted, zero_division=0)),
            "f1": float(f1_score(y, predicted, zero_division=0)),
            "false_positive_rate": float(fp / (fp + tn)) if fp + tn else None,
            "confusion_matrix": [[int(tn), int(fp)], [int(fn), int(tp)]],
            "confusion_order": ["benign", "attack"],
            "per_family": {family: {"support": int(mask.sum()),
                                     "alert_rate": float(predicted[mask].mean())}
                           for family in sorted(rows.family.unique())
                           if (mask := rows.family.eq(family).to_numpy()).any()}}


def score_model(model: Pipeline, rows: pd.DataFrame, anomaly: bool) -> np.ndarray:
    x = rows.loc[:, FEATURE_COLUMNS]
    return -model.score_samples(x) if anomaly else model.predict_proba(x)[:, 1]


def run(dataset: str, seed: int, protocol: str) -> dict:
    print(f"Preparing {dataset} / {protocol} / seed {seed}", flush=True)
    frame = pd.read_parquet(WORK / f"prepared/{dataset}.parquet")
    parts, split_summary = split(frame, seed, protocol)
    run_id = f"{dataset}-{protocol}-{seed}"
    directory = WORK / "runs" / run_id
    directory.mkdir(parents=True, exist_ok=True)
    pd.concat([rows.assign(partition=key) for key, rows in parts.items()]).to_parquet(directory / "partitions.parquet", index=False)
    result = {"run_id": run_id, "dataset": dataset, "seed": seed, "protocol": protocol,
              "feature_version": FEATURE_VERSION, "features": list(FEATURE_COLUMNS),
              "prepared_sha256": digest(WORK / f"prepared/{dataset}.parquet"),
              "split": split_summary, "models": {}}
    train, val, test = (parts[key] for key in ("train", "validation", "test"))
    training_hashes = set(pd.util.hash_pandas_object(train.loc[:, FEATURE_COLUMNS], index=False))
    distinct_mask = ~pd.util.hash_pandas_object(test.loc[:, FEATURE_COLUMNS], index=False).isin(training_hashes).to_numpy()
    constructors = {
        "logistic_regression": LogisticRegression(C=1, class_weight="balanced", max_iter=1500, random_state=seed),
        "random_forest": RandomForestClassifier(n_estimators=120, max_depth=16, min_samples_leaf=5,
                                                class_weight="balanced", n_jobs=2, random_state=seed),
        "isolation_forest": IsolationForest(n_estimators=120, max_samples=2048, n_jobs=2, random_state=seed),
    }
    for name, classifier in constructors.items():
        anomaly = name == "isolation_forest"
        fit_rows = train.loc[train.label.eq(0)] if anomaly else train
        model = Pipeline([("features", transform()), ("model", classifier)])
        started = time.perf_counter()
        with threadpool_limits(limits=2):
            model.fit(fit_rows.loc[:, FEATURE_COLUMNS], None if anomaly else fit_rows.label)
        fit_seconds = time.perf_counter() - started
        validation_scores = score_model(model, val, anomaly)
        threshold = operating_threshold(validation_scores, val.label.to_numpy())
        started = time.perf_counter()
        scores = score_model(model, test, anomaly)
        prediction_seconds = time.perf_counter() - started
        output = directory / f"{name}.joblib"
        bundle = {"feature_version": FEATURE_VERSION, "feature_columns": list(FEATURE_COLUMNS),
                  "model": model, "threshold": threshold, "kind": name,
                  "dataset": dataset, "run_id": run_id, "versions": {
                      "sklearn": sklearn.__version__, "numpy": np.__version__, "pandas": pd.__version__, "joblib": joblib.__version__}}
        joblib.dump(bundle, output, compress=3)
        per_model = {"fit_seconds": fit_seconds, "inference_ms_per_1000": prediction_seconds / len(test) * 1e6,
                     "artifact_bytes": output.stat().st_size, "artifact_sha256": digest(output),
                     "fit_rows": len(fit_rows), "threshold": threshold,
                     "validation": metrics(val, validation_scores, threshold),
                     "test": metrics(test, scores, threshold),
                     "unseen_feature_vectors": metrics(test.loc[distinct_mask], scores[distinct_mask], threshold) if distinct_mask.any() else None,
                     "feature_vector_overlap_fraction": float(1 - distinct_mask.mean()),
                     "unseen_test_families": sorted(set(test.family) - set(train.family)),
                     "default_threshold_test": metrics(test, scores, .5) if not anomaly else None}
        known = test.label.eq(0) | test.family.isin(set(train.family))
        per_model["known_family_test"] = metrics(test.loc[known], scores[known], threshold)
        result["models"][name] = per_model
        print(json.dumps({"run": run_id, "model": name, "fit_seconds": fit_seconds, "threshold": threshold, "test": per_model["test"]}), flush=True)
        (directory / "metrics.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    parser.add_argument("--datasets", nargs="+", choices=["ton", "cic"], default=["ton", "cic"])
    parser.add_argument("--temporal", action="store_true", help="Supplementary within-scenario chronological CIC evaluation")
    args = parser.parse_args()
    for dataset in args.datasets:
        for seed in args.seeds:
            run(dataset, seed, "endpoint_pairs")
    if args.temporal:
        run("cic", args.seeds[0], "within_scenario_time")
    environment = {"python": platform.python_version(), "platform": platform.platform(),
                   "sklearn": sklearn.__version__, "pandas": pd.__version__, "numpy": np.__version__,
                   "joblib": joblib.__version__, "limits": LIMITS, "target_validation_fpr": TARGET_FPR}
    (WORK / "environment.json").write_text(json.dumps(environment, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
