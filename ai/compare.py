"""Report repeated holdouts and cross-dataset transfer without refitting or tuning."""
import json

import joblib
import numpy as np
import pandas as pd

from ai.acquire import WORK
from ai.experiment import metrics, score_model, ROOT

MODELS = ("logistic_regression", "random_forest", "isolation_forest")


def balanced(rows: pd.DataFrame) -> pd.DataFrame:
    count = min(10000, int(rows.label.value_counts().min()))
    if count < 1:
        raise ValueError("Cannot balance a single-class heldout")
    return pd.concat([rows.loc[rows.label.eq(label)].sample(n=count, random_state=123) for label in (0, 1)])


def main() -> None:
    runs = [json.loads(p.read_text()) for p in sorted((WORK / "runs").glob("*/metrics.json"))]
    # Add explicitly separated known-family results, including for existing completed runs.
    for run in runs:
        partitions = pd.read_parquet(WORK / "runs" / run["run_id"] / "partitions.parquet")
        train = partitions.loc[partitions.partition.eq("train")]
        test = partitions.loc[partitions.partition.eq("test")]
        known = test.label.eq(0) | test.family.isin(set(train.family))
        for name in MODELS:
            if "known_family_test" not in run["models"][name]:
                bundle = joblib.load(WORK / "runs" / run["run_id"] / f"{name}.joblib")
                scores = score_model(bundle["model"], test, name == "isolation_forest")
                run["models"][name]["known_family_test"] = metrics(test.loc[known], scores[known], bundle["threshold"])
    aggregate = {}
    for dataset in ("ton", "cic"):
        aggregate[dataset] = {}
        relevant = [run for run in runs if run["dataset"] == dataset and run["protocol"] == "endpoint_pairs"]
        for model in MODELS:
            values = [run["models"][model] for run in relevant]
            aggregate[dataset][model] = {
                "runs": len(values),
                **{metric: {"mean": float(np.mean([v["test"][metric] for v in values])),
                            "min": float(min(v["test"][metric] for v in values)),
                            "max": float(max(v["test"][metric] for v in values))}
                   for metric in ("precision", "recall", "f1", "false_positive_rate")},
                "mean_fit_seconds": float(np.mean([v["fit_seconds"] for v in values])),
                "mean_inference_ms_per_1000": float(np.mean([v["inference_ms_per_1000"] for v in values])),
                "mean_artifact_bytes": float(np.mean([v["artifact_bytes"] for v in values])),
            }
    transfer, matched = [], []
    for seed in (42, 43, 44):
        for source, target in (("ton", "cic"), ("cic", "ton")):
            rows = pd.read_parquet(WORK / f"runs/{target}-endpoint_pairs-{seed}/partitions.parquet")
            rows = rows.loc[rows.partition.eq("test")]
            for name in MODELS:
                bundle = joblib.load(WORK / f"runs/{source}-endpoint_pairs-{seed}/{name}.joblib")
                scores = score_model(bundle["model"], rows, name == "isolation_forest")
                transfer.append({"source": source, "target": target, "seed": seed, "model": name,
                                 "metrics": metrics(rows, scores, bundle["threshold"])})
                # Matched prevalence does not make different attack families equivalent.
                same = pd.read_parquet(WORK / f"runs/{source}-endpoint_pairs-{seed}/partitions.parquet")
                same = balanced(same.loc[same.partition.eq("test")])
                same_scores = score_model(bundle["model"], same, name == "isolation_forest")
                matched.append({"dataset": source, "seed": seed, "model": name,
                                "metrics": metrics(same, same_scores, bundle["threshold"])})
    report = {"aggregate": aggregate, "transfer": transfer, "matched_prevalence": matched,
              "runs": runs, "audits": {name: json.loads((WORK / f"prepared/{name}.audit.json").read_text()) for name in ("ton", "cic")},
              "sources": json.loads((WORK / "sources.json").read_text()),
              "environment": json.loads((WORK / "environment.json").read_text())}
    output = ROOT / "ai/reports"
    output.mkdir(exist_ok=True)
    (output / "comparison.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    flat = []
    for run in runs:
        for name, result in run["models"].items():
            flat.append({"dataset": run["dataset"], "protocol": run["protocol"], "seed": run["seed"], "model": name,
                         **{key: result["test"][key] for key in ("rows", "precision", "recall", "f1", "false_positive_rate")},
                         "threshold": result["threshold"], "confusion_matrix": json.dumps(result["test"]["confusion_matrix"]),
                         "fit_seconds": result["fit_seconds"], "inference_ms_per_1000": result["inference_ms_per_1000"],
                         "artifact_bytes": result["artifact_bytes"]})
    pd.DataFrame(flat).to_csv(output / "metrics.csv", index=False)
    print(json.dumps({"aggregate": aggregate, "transfer_seed42": [r for r in transfer if r['seed'] == 42]}, indent=2), flush=True)


if __name__ == "__main__":
    main()
