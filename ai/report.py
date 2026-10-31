"""Render measured experiment results; never substitutes missing measurements."""
import json
from datetime import datetime, timezone

from ai.acquire import ROOT


def percent(value):
    return f"{value * 100:.2f}%"


def main():
    directory = ROOT / "ai/reports"
    data = json.loads((directory / "comparison.json").read_text())
    resources = json.loads((directory / "runtime_resources.json").read_text())
    verification = json.loads((directory / "manual_verification.json").read_text())
    deployment = json.loads((ROOT / "api/app/ai/deployment.json").read_text())
    lines = ["# Measured connection classifier comparison", "",
             f"Report generated {datetime.now(timezone.utc).date()}. Binary labels: benign=0, attack=1. All values below come from executed local runs.",
             "No VM experiment or raw-PCAP re-extraction was performed locally. See ../README.md for the full protocol and reproduction commands.", "",
             "## Data audit", "",
             "| Dataset | Raw rows | Exact duplicates removed | Remaining rows | Endpoint-pair groups | Timestamps |",
             "|---|---:|---:|---:|---:|---|"]
    for dataset, audit in data["audits"].items():
        lines.append(f"| {dataset} | {sum(f['raw_rows'] for f in audit['files']):,} | {sum(f['duplicate_rows_removed'] for f in audit['files']):,} | {audit['rows']:,} | {audit['groups']:,} | {audit['timestamp_available']} |")
    lines += ["", "TON uses a version-pinned community network subset, not the complete raw collection. CIC uses a published five-day Zeek derivative, not CICFlowMeter CSVs or CNS2022 corrected labels. Hashes and provenance are in comparison.json.",
              "The CIC derivative's exact Zeek version and full label implementation are unverified. Capture gaps and weak annotation remain potential confounders. Source confidence/evidence fields are never inputs.", "",
              "## Comparable grouped runs: mean over seeds 42, 43, 44", "",
              "Unweighted means across three different endpoint-pair partitions; no confidence interval is claimed. The held-out attack prevalence and family coverage differ across datasets and seeds. These means include previously absent attack families; they are not purely known-attack scores.", "",
              "| Dataset | Model | Precision | Recall | F1 | FPR | Recall range |",
              "|---|---|---:|---:|---:|---:|---|"]
    for dataset, models in data["aggregate"].items():
        for name, values in models.items():
            lines.append(f"| {dataset} | {name} | " + " | ".join(percent(values[m]["mean"]) for m in ("precision", "recall", "f1", "false_positive_rate")) + f" | {percent(values['recall']['min'])} - {percent(values['recall']['max'])} |")
    lines += ["", "Thresholds target 1% FPR on benign validation records only. This does not guarantee 1% held-out FPR. No threshold tuning uses held-out data.", "",
              "## All individual runs and confusion matrices", "",
              "Matrix format: [[TN, FP], [FN, TP]]. For Isolation Forest, 'attack' in this scoring table is the ground-truth evaluation target; its own output is only an unusualness score.", "",
              "| Dataset / protocol / seed | Model | Precision | Recall | F1 | FPR | Confusion matrix |",
              "|---|---|---:|---:|---:|---:|---|"]
    for run in data["runs"]:
        for name, values in run["models"].items():
            metric = values["test"]
            lines.append(f"| {run['run_id']} | {name} | " + " | ".join(percent(metric[m]) for m in ("precision", "recall", "f1", "false_positive_rate")) + f" | `{metric['confusion_matrix']}` |")
    lines += ["", "The CIC within-scenario-time supplement splits each family's timeline, purges connections crossing boundaries and adds a 60-second embargo. It still shares campaigns and endpoints; it is not evidence from independent future attacks. TON has no timestamps in this subset, so no equivalent temporal score exists.", "",
              "## Frozen cross-dataset transfer", "",
              "No target refitting, target preprocessing fit or target threshold tuning. Different label families make these stress evaluations rather than matched attack comparisons.", "",
              "| Source -> target / seed | Model | Precision | Recall | F1 | FPR |",
              "|---|---|---:|---:|---:|---:|"]
    for value in data["transfer"]:
        lines.append(f"| {value['source']} -> {value['target']} / {value['seed']} | {value['model']} | " + " | ".join(percent(value["metrics"][m]) for m in ("precision", "recall", "f1", "false_positive_rate")) + " |")
    lines += ["", "## Selection and scope", "",
              "The initial deployment uses the CIC grouped reference run (seed 42), Random Forest, with its unchanged validation-calibrated threshold. Seed 42 was the fixed reference, not the best held-out seed. Mean validation recall across the three partitions is:", "",
              "| Dataset | Model | Mean validation recall |",
              "|---|---|---:|"]
    for dataset in ("ton", "cic"):
        relevant = [run for run in data["runs"] if run["dataset"] == dataset and run["protocol"] == "endpoint_pairs"]
        for name in ("logistic_regression", "random_forest"):
            mean = sum(run["models"][name]["validation"]["recall"] for run in relevant) / len(relevant)
            lines.append(f"| {dataset} | {name} | {percent(mean)} |")
    lines += ["", "Reasons: a shared Zeek feature contract; a broader workstation/service background in CIC; strong Random Forest validation results at the chosen FPR budget; very high TON-to-CIC false alarms; and small inference artifacts. TON's higher internal F1 is not treated as proof of better applicability.",
              "CIC is the better initial baseline for this application, not a validated deployment-quality detector. CIC seed 44 exposes a major limitation: entire attack families move outside training and recall falls sharply. Cross-domain scores likewise do not establish generalization. Both datasets remain useful; neither replaces controlled local validation.",
              "Isolation Forest has very low attack recall at the selected operating points. It remains an offline anomaly experiment and is not activated. No combined classifier/anomaly system is claimed.",
              "The deployed binary model emits only Suspicious Connection findings requiring review. It does not identify specific attack families, certify anomalies as attacks, or provide calibrated attack probabilities. The absence of a finding is not proof of safety.", "",
              "## Selected run: family coverage", "",
              "| Family | Training support | Held-out support | Binary detection rate |",
              "|---|---:|---:|---:|"]
    selected = next(run for run in data["runs"] if run["run_id"] == deployment["run_id"])
    trained = selected["split"]["train"]["used_families"]
    families = selected["models"][deployment["model"]]["test"]["per_family"]
    for family in sorted(set(trained) | set(families)):
        support = families.get(family)
        lines.append(f"| {family} | {trained.get(family, 0)} | {support['support'] if support else 0} | {percent(support['alert_rate']) if support else 'not evaluated'} |")
    lines += ["", "The benign row is a false-positive rate. One or a few records never establish attack-category performance. Detailed results for known-family-only and distinct-feature-vector sensitivity are in comparison.json.", "",
              "## Resources", "",
              f"- Selected compressed artifact: {resources['selected_artifact_bytes']:,} bytes.",
              f"- Model load in a fresh process: {resources['model_load_seconds']:.3f} seconds.",
              f"- Median prediction time for {resources['rows']} prepared records: {resources['median_batch_ms']:.2f} ms.",
              f"- Peak process RSS including imports, model and held-out table: {resources['peak_process_rss_bytes'] / 1024**2:.1f} MiB.",
              "- Host CPU measurements only; no claim of measured laptop performance or combined VM/application memory consumption.", "",
              "## Executed verification", "",
              f"- {verification['records_prepared']} real held-out records were normalized and saved in a separate temporary SQLite database.",
              f"- Offline/DTO/stored feature parity verified; manual API analysis persisted {verification['persisted_alerts']} findings, matching direct classifier predictions.",
              "- Cookie login, unauthorized access refusal, detector health, session completion, evidence links and logout verified through ASGI requests.",
              "- Missing values initially changed through ORM zero defaults; corrected normalization/storage and repeated the parity/API check successfully.",
              "- Frontend build and lint completed; build retains a bundle-size warning. Python compilation, dependency consistency and whitespace checks completed.",
              "- No automated test suite was added. Production database and VM configuration were not modified.", "",
              "## Remaining validation", "",
              "Measure benign alarm rates and controlled attack recall on the real VM path; inspect Zeek 9 checksum policy, capture loss and extractor compatibility; calibrate using independently recorded benign lab data; evaluate on untouched local holdouts and on the laptop. Do not tune repeatedly on the same holdout. More protocol/security context and meaningful behavioral windows require additional work.", ""]
    (directory / "experiment_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(directory / "experiment_report.md")


if __name__ == "__main__":
    main()
