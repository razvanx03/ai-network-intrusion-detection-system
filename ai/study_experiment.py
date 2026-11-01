"""Source/feature ablations and frozen transfer on common untouched partitions.

python -m ai.study_experiment --datasets cic uwf ctu --seeds 42 43 44
No artifact here is deployed automatically. No VM/database/config is accessed.
"""
import argparse
import json
import os
from pathlib import Path
import sys
import time
import warnings

os.environ.setdefault("OMP_NUM_THREADS", "2")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "api"))
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from threadpoolctl import threadpool_limits

from app.ai.features import FEATURE_COLUMNS, CATEGORICAL
from ai.experiment import split, metrics, operating_threshold, bounded, LIMITS
from ai.study_acquire import STUDY, digest
from ai.study_prepare import DERIVED, HISTORY

FEATURE_SETS = {"core": tuple(FEATURE_COLUMNS),
                "derived": tuple(FEATURE_COLUMNS) + DERIVED,
                "history": tuple(FEATURE_COLUMNS) + DERIVED + HISTORY}
VERSION = "extension-study-v1"


def classifier(kind, columns, seed):
    numeric = [name for name in columns if name not in CATEGORICAL]
    preprocessing = ColumnTransformer([
        ("numeric", StandardScaler(), numeric),
        ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), list(CATEGORICAL)),
    ])
    estimator = (RandomForestClassifier(n_estimators=120, max_depth=16, min_samples_leaf=5,
                class_weight="balanced", n_jobs=2, random_state=seed) if kind == "random_forest" else
                LogisticRegression(C=1, class_weight="balanced", max_iter=1500, random_state=seed))
    return Pipeline([("features", preprocessing), ("model", estimator)])


def evaluation(model, rows, columns, threshold, training=None):
    start = time.perf_counter()
    with threadpool_limits(limits=2):
        scores = model.predict_proba(rows.loc[:, columns])[:, 1]
    result = metrics(rows, scores, threshold)
    result["inference_ms_per_500"] = (time.perf_counter() - start) / len(rows) * 500000
    if training is not None:
        known = set(pd.util.hash_pandas_object(training.loc[:, columns], index=False))
        distinct = ~pd.util.hash_pandas_object(rows.loc[:, columns], index=False).isin(known).to_numpy()
        result["training_feature_vector_overlap"] = float(1 - distinct.mean())
        result["distinct_feature_vectors"] = metrics(rows.loc[distinct], scores[distinct], threshold) if distinct.any() else None
    return result


def partitions(frame, seed, mode):
    if mode == "endpoint_pairs":
        return split(frame, seed, mode)
    if mode == "devices":
        selected = frame.capture.str.contains("Windows7full-1", regex=False)
        if not selected.any() or selected.all():
            raise ValueError("Device holdout needs the Windows full-1 and separate captures")
        outer = frame.loc[~selected]
        # Different device PCAPs may observe the same communication. Purge ALL
        # outer endpoint pairs before fitting, not merely duplicate Zeek UIDs.
        fit = frame.loc[selected & ~frame.group.isin(set(outer.group))]
        train_indices, validation_indices = next(GroupShuffleSplit(
            n_splits=1, test_size=.25, random_state=42).split(fit, groups=fit.group))
        parts = {"train": bounded(fit.iloc[train_indices], LIMITS["train"], 42),
                 "validation": bounded(fit.iloc[validation_indices], LIMITS["validation"], 42),
                 "test": bounded(outer, LIMITS["test"], 42)}
        summary = {key: {"used": len(rows), "families": rows.family.value_counts().to_dict()}
                   for key, rows in parts.items()}
        summary["held_out_devices"] = sorted(outer.capture.unique())
        summary["purged_shared_pair_rows"] = int(selected.sum() - len(fit))
        for key, rows in parts.items():
            # Calibration deliberately uses benign validation rows only; the
            # validation set need not contain attacks. No seed is retried.
            if key != "validation" and set(rows.label.unique()) != {0, 1}:
                raise ValueError(f"Device {key} has no two-class support")
        return parts, summary
    # Whole capture days stay together; no IP/date/UID is a predictor. UWF has
    # malicious spring captures and benign autumn captures, so this diagnostic
    # reserves dates independently within each label, rather than pretending a
    # global chronological binary split is feasible.
    selections = {key: [] for key in LIMITS}
    # UWF's two classes occur in disjoint seasons. Mark its within-class date
    # test as a diagnostic, not an independent global chronological deployment.
    labels = [0, 1] if set(frame.loc[frame.label.eq(0), "day"]).isdisjoint(set(frame.loc[frame.label.eq(1), "day"])) else [None]
    for label in labels:
        rows = frame if label is None else frame.loc[frame.label.eq(label)]
        days = sorted(rows.day.unique())
        if len(days) < 3:
            raise ValueError("Insufficient dates for capture-day diagnostic")
        first, second = max(1, int(.6 * len(days))), max(2, int(.8 * len(days)))
        for key, chosen in zip(LIMITS, [days[:first], days[first:second], days[second:]], strict=True):
            part = rows.loc[rows.day.isin(chosen)]
            # Purge long connections crossing a selected day's end.
            day_end = pd.to_datetime(part.day, utc=True).dt.as_unit("ns").astype("int64") / 1e9 + 86400
            selections[key].append(part.loc[(part.event_time + part.duration_raw).lt(day_end)])
    parts = {key: bounded(pd.concat(values), LIMITS[key], seed) for key, values in selections.items()}
    for key, rows in parts.items():
        if set(rows.label.unique()) != {0, 1}:
            raise ValueError(f"{key} lacks two-class support")
    for first, second in [("train", "validation"), ("train", "test"), ("validation", "test")]:
        if set(parts[first].day) & set(parts[second].day):
            raise ValueError("Capture-day overlap")
    return parts, {key: {"used": len(rows), "days": sorted(rows.day.unique()),
                        "families": rows.family.value_counts().to_dict()} for key, rows in parts.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", nargs="+", choices=["cic", "uwf", "ctu"], required=True)
    parser.add_argument("--seeds", nargs="+", type=int, default=[42, 43, 44])
    parser.add_argument("--features", nargs="+", choices=list(FEATURE_SETS), default=list(FEATURE_SETS))
    parser.add_argument("--protocol", choices=["endpoint_pairs", "capture_days", "devices"], default="endpoint_pairs")
    parser.add_argument("--mixed", action="store_true")
    parser.add_argument("--partition-seed", type=int, default=42)
    args = parser.parse_args()
    protocol_label = args.protocol + (f"_p{args.partition_seed}" if args.partition_seed != 42 else "")
    directory = STUDY / "results_serial"
    directory.mkdir(parents=True, exist_ok=True)
    source_hashes = {name: digest(STUDY / f"prepared/{name}.parquet") for name in args.datasets}
    manifest = json.loads((ROOT / "api/app/ai/deployment.json").read_text())
    selected_path = ROOT / "api/app/ai" / manifest["artifact"]
    if digest(selected_path) != manifest["sha256"]:
        raise ValueError("Deployed baseline failed checksum verification")
    deployed = joblib.load(selected_path)
    deployed["model"].set_params(model__n_jobs=1)
    for seed in args.seeds:
        prepared, summaries = {}, {}
        for dataset in args.datasets:
            frame = pd.read_parquet(STUDY / f"prepared/{dataset}.parquet")
            # Freeze evaluation partitions at the deployed reference split.
            # Evaluating the deployed seed-42 model on a seed-43 CIC test set
            # would accidentally include records it saw during training.
            effective_protocol = "endpoint_pairs" if dataset == "cic" or (dataset == "uwf" and args.protocol == "devices") else args.protocol
            partition_seed = 42 if dataset == "cic" else args.partition_seed
            prepared[dataset], summaries[dataset] = partitions(frame, partition_seed, effective_protocol)
            summaries[dataset]["effective_protocol"] = effective_protocol
            summaries[dataset]["partition_seed"] = partition_seed
            del frame
        baseline_path = directory / f"deployed-{protocol_label}-{seed}.json"
        baseline = {"study_version": VERSION, "source_hashes": source_hashes,
                    "baseline_sha256": manifest["sha256"], "protocol": protocol_label, "seed": seed, "partition_seed": args.partition_seed,
                    "split": summaries, "targets": {name: evaluation(deployed["model"], parts["test"],
                        FEATURE_COLUMNS, deployed["threshold"], prepared.get("cic", {}).get("train")) for name, parts in prepared.items()}}
        baseline_path.write_text(json.dumps(baseline, indent=2), encoding="utf-8")
        sources = list(args.datasets) + (["mixed"] if args.mixed else [])
        for source in sources:
            if source == "mixed":
                train = pd.concat([bounded(parts["train"], LIMITS["train"] // len(prepared), 42)
                                   for parts in prepared.values()], ignore_index=True)
                calibrations = [parts["validation"] for parts in prepared.values()]
            else:
                train = prepared[source]["train"]
                calibrations = [prepared[source]["validation"]]
            for feature_set in args.features:
                columns = FEATURE_SETS[feature_set]
                for kind in ["random_forest", "logistic_regression"]:
                    source_id = source + ("-" + "-".join(args.datasets) if source == "mixed" else "")
                    identifier = f"{source_id}-{feature_set}-{kind}-{protocol_label}-{seed}"
                    target = directory / f"{identifier}.json"
                    if target.exists():
                        prior = json.loads(target.read_text())
                        compatible = all(source_hashes.get(name) == checksum
                                         for name, checksum in prior.get("source_hashes", {}).items())
                        if compatible and prior.get("study_version") == VERSION and (source != "mixed" or prior["source_hashes"] == source_hashes):
                            missing_targets = {name for name in prepared if name not in prior["targets"]
                                               or "training_feature_vector_overlap" not in prior["targets"][name]}
                            if missing_targets:
                                artifact = directory / f"{identifier}.joblib"
                                if digest(artifact) != prior["artifact_sha256"]:
                                    raise ValueError("Cached study artifact changed")
                                bundle = joblib.load(artifact)
                                for name in sorted(missing_targets):
                                    prior["targets"][name] = evaluation(bundle["model"], prepared[name]["test"], columns, prior["threshold"], train)
                                prior["source_hashes"], prior["split"] = source_hashes, summaries
                                target.write_text(json.dumps(prior, indent=2), encoding="utf-8")
                            print("Cached", identifier, flush=True)
                            continue
                        raise ValueError("Study inputs changed; choose a new result directory/version")
                    previous = STUDY / "results" / f"{identifier}.json"
                    reused = False
                    if previous.exists():
                        previous_result = json.loads(previous.read_text())
                        previous_artifact = previous.with_suffix(".joblib")
                        if previous_result["source_hashes"] == source_hashes:
                            if digest(previous_artifact) != previous_result["artifact_sha256"]:
                                raise ValueError("Original fitted study artifact changed")
                            model = joblib.load(previous_artifact)["model"]
                            fit_seconds = previous_result["fit_seconds"]
                            fit_warnings = previous_result["fit_warnings"]
                            reused = True
                    if not reused:
                        model = classifier(kind, columns, seed)
                        start = time.perf_counter()
                        with threadpool_limits(limits=2), warnings.catch_warnings(record=True) as caught:
                            warnings.simplefilter("always", ConvergenceWarning)
                            model.fit(train.loc[:, columns], train.label)
                        fit_seconds = time.perf_counter() - start
                        fit_warnings = [str(item.message) for item in caught]
                    if kind == "random_forest":
                        # Fixed tree aggregation order prevents one-ULP changes
                        # from moving tied scores across the calibrated boundary.
                        model.set_params(model__n_jobs=1)
                    thresholds = []
                    for validation in calibrations:
                        with threadpool_limits(limits=2):
                            scores = model.predict_proba(validation.loc[:, columns])[:, 1]
                        thresholds.append(operating_threshold(scores, validation.label.to_numpy()))
                    # Mixed training must meet the benign validation budget for
                    # each contributing domain; use the most conservative threshold.
                    threshold = max(thresholds)
                    result = dict(study_version=VERSION, id=identifier, source=source,
                        feature_set=feature_set, features=list(columns), kind=kind, seed=seed,
                        protocol=protocol_label, partition_seed=args.partition_seed, source_hashes=source_hashes, train_rows=len(train),
                        fit_seconds=fit_seconds, threshold=threshold,
                        validation_target_fpr=.01, threshold_rule="max domain benign 99th quantile plus nextafter",
                        inference_workers=1, reused_fitted_weights=reused, fit_warnings=fit_warnings,
                        split=summaries, targets={})
                    for name, parts in prepared.items():
                        result["targets"][name] = evaluation(model, parts["test"], columns, threshold, train)
                    artifact = directory / f"{identifier}.joblib"
                    joblib.dump({"model": model, "feature_columns": list(columns), "threshold": threshold,
                                 "study_version": VERSION, "source_hashes": source_hashes}, artifact, compress=3)
                    result["artifact_bytes"] = artifact.stat().st_size
                    result["artifact_sha256"] = digest(artifact)
                    target.write_text(json.dumps(result, indent=2), encoding="utf-8")
                    print(json.dumps(dict(id=identifier, fit_seconds=fit_seconds,
                        targets={name: {key: values[key] for key in ["precision", "recall", "f1", "false_positive_rate"]}
                                 for name, values in result["targets"].items()})), flush=True)


if __name__ == "__main__":
    main()
