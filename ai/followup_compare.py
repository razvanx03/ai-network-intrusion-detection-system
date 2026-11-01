"""Frozen transfer matrix, including new CIC inputs; no threshold tuning on targets."""
import argparse
import json
import time


def main():
    import joblib
    import numpy as np
    import pandas as pd
    from threadpoolctl import threadpool_limits
    from ai.cic_followup import WORK, ROOT
    from ai.experiment import metrics
    from ai.live_study import candidate_paths, digest
    from ai.study_experiment import partitions
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--targets", nargs="+", choices=["cic", "uwf", "ctu", "cic2018", "cic2018_day", "cic2019"], required=True)
    args = parser.parse_args()
    targets, fingerprints = {}, {}
    for target in args.targets:
        if target in ("cic2018", "cic2018_day", "cic2019"):
            path = WORK / f"prepared/{target}.parquet"
            if target.startswith("cic2018"):
                name = "cic2018-capture_day" if target.endswith("_day") else "cic2018"
                path = WORK / f"prepared/{name}-partitions.parquet"
                frame = pd.read_parquet(path)
                targets[target] = frame.loc[frame.partition.eq("test")].copy()
            else:
                targets[target] = pd.read_parquet(path)
        else:
            path = ROOT / f".ai-workspace/extension/prepared/{target}.parquet"
            frame = pd.read_parquet(path)
            targets[target] = partitions(frame, 42, "endpoint_pairs")[0]["test"]
        fingerprints[target] = {"sha256": digest(path), "rows": len(targets[target])}
        if "frame" in locals():
            del frame
    out = WORK / "transfer-results.json"
    report = json.loads(out.read_text()) if out.exists() else {"targets": {}, "models": {}}
    for target, fingerprint in fingerprints.items():
        if target in report["targets"] and report["targets"][target] != fingerprint:
            raise ValueError("Frozen evaluation target changed; choose a new study output")
        report["targets"][target] = fingerprint
    for name, path in candidate_paths():
        checksum = digest(path)
        if name == "deployed-cic2017":
            manifest = json.loads((ROOT / "api/app/ai/deployment.json").read_text())
            if checksum != manifest["sha256"]:
                raise ValueError("Deployed baseline failed checksum verification")
        previous = report["models"].setdefault(name, {"sha256": checksum, "targets": {}})
        if previous["sha256"] != checksum:
            raise ValueError("Candidate artifact changed during study")
        needed = [target for target in targets if target not in previous["targets"]]
        if not needed:
            continue
        bundle = joblib.load(path)
        model, columns = bundle["model"], bundle["feature_columns"]
        if "model__n_jobs" in model.get_params():
            model.set_params(model__n_jobs=1)
        for target in needed:
            if name.startswith("cic2018-") and ((target == "cic2018_day" and "capture_day" not in name)
                    or (target == "cic2018" and "capture_day" in name)):
                previous["targets"][target] = {"unsupported": "Different 2018 training partition can overlap this target; use the corresponding native holdout only"}
                continue
            if target == "cic" and name.startswith("cic-") and name.endswith(("-43", "-44")) and "endpoint_pairs" not in name:
                previous["targets"][target] = {"unsupported": "Original split differs from frozen seed-42 CIC holdout; overlap would leak training rows"}
                continue
            started = time.perf_counter()
            rows = targets[target]
            with threadpool_limits(limits=1):
                x = rows.loc[:, columns]
                scores = -model.score_samples(x) if bundle.get("kind") == "isolation_forest" else model.predict_proba(x)[:, 1]
            if not np.isfinite(scores).all():
                raise ValueError("Nonfinite transfer evaluation scores")
            previous["targets"][target] = metrics(rows, scores, bundle["threshold"])
            previous["targets"][target]["inference_seconds"] = time.perf_counter()-started
        out.write_text(json.dumps(report, indent=2))
        print(name, "evaluated", ",".join(needed), flush=True)
        del model, bundle


if __name__ == "__main__":
    main()
