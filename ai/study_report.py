"""Publish measured extension-study results without source traffic or artifacts."""
from collections import defaultdict
from datetime import datetime, timezone
import json
import statistics

from ai.study_acquire import ROOT, STUDY, digest

METRICS = ("precision", "recall", "f1", "false_positive_rate")


def main():
    paths = sorted((STUDY / "results_serial").glob("*.json"))
    records = [json.loads(path.read_text()) for path in paths]
    # Two-source exploratory runs remain on disk, but do not enter the final
    # three-source comparison. Every retained target has the same split seed.
    records = [record for record in records if set(record["source_hashes"]) == {"cic", "uwf", "ctu"}]
    groups = defaultdict(list)
    baselines = {}
    for record in records:
        if "source" not in record:
            baselines[record["protocol"]] = record
            continue
        groups[(record["protocol"], record["source"], record["feature_set"], record["kind"])].append(record)
    summaries = []
    expected = set()
    for protocol, seeds, features in [
        ("endpoint_pairs", [42, 43, 44], ["core", "derived", "history"]),
        ("endpoint_pairs_p43", [42], ["core"]),
        ("endpoint_pairs_p44", [42], ["core"]),
        ("capture_days", [42], ["core", "derived", "history"]),
        ("devices", [42], ["core", "history"]),
    ]:
        for seed in seeds:
            for feature in features:
                for source in ["cic", "uwf", "ctu", "mixed"]:
                    for kind in ["random_forest", "logistic_regression"]:
                        expected.add((protocol, seed, feature, source, kind))
    observed = {(value["protocol"], value["seed"], value["feature_set"], value["source"], value["kind"])
                for value in records if "source" in value}
    if observed != expected:
        raise ValueError(f"Incomplete study: {len(expected - observed)} missing or {len(observed - expected)} unexpected configurations")
    for (protocol, source, features, kind), values in sorted(groups.items()):
        summary = dict(protocol=protocol, source=source, features=features, kind=kind,
                       seeds=sorted(value["seed"] for value in values), targets={})
        for target in ("cic", "uwf", "ctu"):
            summary["targets"][target] = {
                key: dict(mean=statistics.mean(value["targets"][target][key] for value in values),
                          minimum=min(value["targets"][target][key] for value in values),
                          maximum=max(value["targets"][target][key] for value in values)) for key in METRICS}
            summary["targets"][target]["rows"] = values[0]["targets"][target]["rows"]
        summary["fit_seconds_mean"] = statistics.mean(value["fit_seconds"] for value in values)
        summaries.append(summary)
    if not summaries or "endpoint_pairs" not in baselines:
        raise ValueError("Three-source experiments are incomplete")
    output = ROOT / "ai/reports"
    audits = {name: json.loads((STUDY / f"prepared/{name}.audit.json").read_text()) for name in ["cic", "uwf", "ctu"]}
    provenance = {path.name: json.loads(path.read_text()) for path in STUDY.glob("*.sources.json")}
    report = dict(generated_at=datetime.now(timezone.utc).isoformat(),
        study_version="extension-study-v1", partition_seed=42,
        seed_interpretation="Repeated model initializations on fixed held-out partitions, not confidence intervals or independent split replication.",
        current_deployment_sha256=baselines["endpoint_pairs"]["baseline_sha256"],
        deployment_decision="retain_current_model",
        decision_basis="Mixed-source forests improve coverage on the main benchmark but regress on CTU held-out devices. No candidate is established as a better detector for the live network.",
        datasets=audits, sources=provenance, summaries=summaries, baselines=baselines, runs=records,
        code_sha256={path.name: digest(path) for path in (ROOT / "ai").glob("study_*.py")})
    (output / "extension_comparison.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    lines = ["# Connection source and feature extension study", "",
        "All numerical results below were measured locally. The deployed artifact was not replaced.", "",
        "## Decision", "",
        "Retain the existing CIC Random Forest. UWF-only and CTU-only training do not establish a better replacement. A bounded mixed-source forest improves coverage across the main fixed holdouts, but that advantage is not stable when CTU devices and their endpoint pairs are held out. Richer connection features do not remove that failure. No new model is integrated into runtime.",
        "The mixed-source core forest is a useful follow-up candidate, not the new accepted model. The mixed derived profile offers a different recall/false-alarm compromise. Neither is demonstrated to improve live capture results. Extra DNS/HTTP/TLS ingestion or temporal behavior features remain possible future experiments, not measured benefits in this study.", "",
        "## Protocol", "",
        "- Same five numeric and three categorical Zeek fields as the deployed model; no raw IP, UID, date, port or annotation is a predictor.",
        "- Core: 13 transformed inputs. Derived: core plus 8 ratios/rates/missingness indicators. History: derived plus 13 directional Zeek history indicators (not exact TCP flag counts).",
        "- Random Forest and Logistic Regression use the existing estimator settings; train/validation/test caps are 80,000/20,000/40,000 records. Training/native-thread limit per process: two. Forest inference uses one worker for deterministic tree aggregation.",
        "- Primary endpoint-pair partitions and sampling are frozen at seed 42. Estimator seeds 42/43/44 measure initialization sensitivity only. Other splits in the original study remain separate evidence.",
        "- Additional p43/p44 challenges vary the new-domain endpoint partitions, always retaining CIC's original seed-42 partition so the deployed model never sees its own training records as test data.",
        "- The CIC reference partition reproduces the original feature vectors, labels, groups and seed-42 metrics. The deployed model is never evaluated on a new CIC split that could contain its training rows.",
        "- Thresholds use only benign validation scores (99th percentile plus nextafter). Mixed training uses equal per-domain training budgets and the most conservative participating-domain threshold. No held-out threshold tuning.",
        "- Every candidate is evaluated on the same target holdouts. Cross-source precision/F1 differ with target attack prevalence; compare candidate models within a target column, not across unrelated datasets.",
        "- Whole-day diagnostics hold CTU dates out chronologically. UWF's benign and malicious dates occupy different seasons, so its per-class date diagnostic is NOT evidence of global forward-time generalization. CIC keeps its original reference partition in this diagnostic.",
        "- Device diagnostics train CTU models on Windows full-1 and hold out Windows AD and Echo. All endpoint pairs observed in those held-out captures are purged from CTU fitting/calibration. A fixed grouped validation split may be benign-only; threshold calibration needs benign support, not attack labels. No split seed is retried to obtain a better score.",
        "- The device diagnostic also changes attack-family support: full-1 training contains DNS C2 connection attempts, whereas AD/Echo test traffic includes discovery, human attacks and other malware annotations. It is a joint device/campaign/family stress test, not a clean measurement of device shift alone. Family names across different sources are not assumed equivalent.",
        "- Connection duplicates are removed before splitting. UWF secondary Duplicate annotation rows are not separate flows. Conflicting binary identities are excluded. CTU background/unknown is excluded, never silently treated as benign.",
        "- Full metrics include confusion matrices, family support, feature-vector overlap and distinct-vector sensitivity. These are connection-review scores, not calibrated attack probabilities or proof of specific ATT&CK tactics.", "",
        "## Source audit", "",
        "| Source | Retained connections | Benign | Attack | Endpoint-pair groups |",
        "|---|---:|---:|---:|---:|"]
    for name, audit in audits.items():
        lines.append(f"| {name} | {audit['rows']:,} | {audit['labels'].get('0',0):,} | {audit['labels'].get('1',0):,} | {audit['groups']:,} |")
    lines += ["", "UWF: seven dated official Parquet partitions; attack captures are February/March 2024 and benign captures October/November 2024. Time is excluded from predictors, but correlated protocol/background differences can still make classification easy.",
        "CTU: all seven days from two Windows systems (AD and full-1), plus Amazon Echo as a supplementary device. The Linux flood-dominated archive is excluded. This is a selected subset, not the entire CTU population. Archive publisher MD5 checks and local SHA-256 fingerprints are retained in the JSON report.", "",
        "## Frozen deployed baseline", "", "| Target | Precision | Recall | F1 | False-positive rate |", "|---|---:|---:|---:|---:|"]
    for target, values in baselines["endpoint_pairs"]["targets"].items():
        lines.append("| " + target + " | " + " | ".join(f"{values[key]*100:.3f}%" for key in METRICS) + " |")
    for protocol in ["endpoint_pairs", "endpoint_pairs_p43", "endpoint_pairs_p44", "capture_days", "devices"]:
        for kind in ["random_forest", "logistic_regression"]:
            lines += ["", f"## {protocol}: {kind}", "",
                "Each cell is attack recall / benign false-positive rate. Means across listed estimator seeds; no confidence interval is claimed.", "",
                "| Training source | Inputs | Seeds | CIC | UWF | CTU |", "|---|---|---|---:|---:|---:|"]
            for summary in summaries:
                if summary["protocol"] == protocol and summary["kind"] == kind:
                    cells = [f"{summary['targets'][name]['recall']['mean']*100:.3f}% / {summary['targets'][name]['false_positive_rate']['mean']*100:.3f}%" for name in ["cic", "uwf", "ctu"]]
                    lines.append(f"| {summary['source']} | {summary['features']} | {summary['seeds']} | " + " | ".join(cells) + " |")
    lines += ["", "## Scope and limits", "",
        "Native-domain success is not proof of transfer to another network. UWF seasonal separation, scripted repetition, CTU's selected device population, weak/annotation-dependent labels and shared campaigns remain confounders. ATT&CK labels do not establish observability of host-only behavior in connection records.",
        "The original CIC holdout was examined in previous work. It is a fixed regression/transfer benchmark here, not a fresh final acceptance set. Three estimator seeds do not replace independent captures, hosts, campaigns or future-time evaluation.",
        "No new VM capture, benign alarm-rate measurement, controlled VM attack evaluation, or laptop measurement is claimed. No SSH/VM/network/firewall/service configuration or application database was altered. No candidate is automatically deployed.",
        "Parallel forest aggregation changed an otherwise identical control threshold from 0.9001884181650492 to 0.9001884181650491. With identical trees/scalers this changed 119 decisions in the fixed CIC test set. Final results use one inference worker and recalibrate on validation only. Original parallel runs remain in the ignored results directory; final runs are in results_serial. Runtime inference now also fixes one worker, without changing artifact weights, fingerprint or feature schema.",
        "Derived features and directional history were evaluated offline. Behavioral windows and DNS/HTTP/TLS ingestion were not added: those require a separately validated causal context/telemetry contract, beyond a feature-name mapping.",
        "## Implementation verification", "",
        "The complete backend unit suite passed: 229 cases, including eight synthetic feature/partition checks added for this study. Four pre-existing Pydantic deprecation warnings remain. These unit checks do not load a real environment file, dataset, deployed artifact, database or VM.",
        "A separate offline runtime smoke check used 500 real Friday CIC source records (not a new statistical holdout). Schema normalization, typed preparation and the live detector agreed with direct model predictions; six repeated inference calls were identical. No SQL, VM or environment file was accessed by this check. The selected artifact SHA-256 remains 5234d410a219d5bfe8f5943116db48e81f38513151ebc5496d96a564e6fdf38b.",
        "## Reproduction", "", "Run from the repository root, with the recorded Python environment:", "", "```powershell",
        "& api/.venv/Scripts/python.exe -B -m ai.study_acquire --source uwf",
        "& api/.venv/Scripts/python.exe -B -m ai.study_acquire --source ctu",
        "& api/.venv/Scripts/python.exe -B -m ai.study_prepare --datasets cic uwf ctu",
        "& api/.venv/Scripts/python.exe -B -m ai.study_experiment --datasets cic uwf ctu --seeds 42 43 44 --mixed",
        "& api/.venv/Scripts/python.exe -B -m ai.study_experiment --datasets cic uwf ctu --seeds 42 --mixed --protocol capture_days",
        "& api/.venv/Scripts/python.exe -B -m ai.study_experiment --datasets cic uwf ctu --seeds 42 --features core history --mixed --protocol devices",
        "& api/.venv/Scripts/python.exe -B -m ai.study_experiment --datasets cic uwf ctu --seeds 42 --features core --mixed --partition-seed 43",
        "& api/.venv/Scripts/python.exe -B -m ai.study_experiment --datasets cic uwf ctu --seeds 42 --features core --mixed --partition-seed 44",
        "& api/.venv/Scripts/python.exe -B -m ai.study_report", "```", "",
        "Raw downloads, prepared tables and candidate artifacts remain Git-ignored under `.ai-workspace/extension/`. Nothing is staged or committed by these commands."]
    (output / "extension_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Published {len(records)} run records and {len(summaries)} summaries", flush=True)


if __name__ == "__main__":
    main()
