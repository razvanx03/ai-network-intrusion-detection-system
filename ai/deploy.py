"""Select a measured local classifier; no refitting or threshold changes.

python -m ai.deploy --run cic-endpoint_pairs-42 --model random_forest
"""
import argparse
import json
import shutil

from ai.acquire import ROOT, WORK, digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    parser.add_argument("--model", required=True, choices=["logistic_regression", "random_forest"])
    args = parser.parse_args()
    run_directory = (WORK / "runs" / args.run).resolve()
    if not run_directory.is_relative_to((WORK / "runs").resolve()):
        raise ValueError("Run must be inside the local experiment directory")
    evaluation = json.loads((run_directory / "metrics.json").read_text())
    if args.model not in evaluation["models"]:
        raise ValueError("This classifier has not been evaluated")
    source = run_directory / f"{args.model}.joblib"
    expected = evaluation["models"][args.model]["artifact_sha256"]
    if digest(source) != expected:
        raise ValueError("Evaluated classifier has changed since evaluation")
    target = ROOT / "api/app/ai/models/selected.joblib"
    target.parent.mkdir(exist_ok=True)
    shutil.copyfile(source, target)
    manifest = {"enabled": True, "artifact": "models/selected.joblib", "sha256": expected,
                "run_id": args.run, "model": args.model,
                "scope": "Binary suspicious-connection screening; no attack-family or anomaly verdict.",
                "threshold_source": "Benign validation records; target false-positive rate 1%."}
    (target.parent.parent / "deployment.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
