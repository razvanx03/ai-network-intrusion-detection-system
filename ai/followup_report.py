"""Publish measured follow-up evidence without raw traffic, credentials or models."""
import json

from ai.cic_followup import ROOT, WORK
from ai.live_study import digest


def percent(value):
    return f"{100*value:.2f}%"


def main():
    live = json.loads((WORK / "corrected/results.json").read_text())
    if live["sensor_sha256"] != "bbc699f170256a4b6dc33e70dbda2271babe79398385dcd7a1e4f148549b7d97":
        raise ValueError("This report narrative describes the recorded October VM trace; write a new report for different live evidence")
    transfer = json.loads((WORK / "transfer-results.json").read_text())
    native = {name: json.loads((WORK / f"{name}-results.json").read_text())
        for name in ("cic2018", "cic2018-capture_day")}
    capture = json.loads((WORK / "corrected-capture-audit.json").read_text())
    integrity = json.loads((WORK / "transfer-integrity.json").read_text())
    api_probe = json.loads((WORK / "api-live-probe.json").read_text())
    manifest = json.loads((ROOT / "api/app/ai/deployment.json").read_text())
    if digest(ROOT / "api/app/ai/models/selected.joblib") != manifest["sha256"]:
        raise ValueError("Selected baseline changed")
    if live["models"]["deployed-cic2017"]["sha256"] != manifest["sha256"]:
        raise ValueError("Current deployment differs from the recorded baseline")
    if any(item["source_sha256"] != "6e70afc6e952ba25122bf227bb5f7b15e751c9b571f368b8eb2443cd1450ffbd" for item in native.values()):
        raise ValueError("This report narrative requires the recorded 2018 cohort")
    if digest(WORK / "corrected/sensor.jsonl") != live["sensor_sha256"]:
        raise ValueError("Saved VM evidence changed")
    if set(live["models"]) != set(transfer["models"]):
        raise ValueError("Live and offline candidate inventories differ")
    for name, result in live["models"].items():
        if result["sha256"] != transfer["models"][name]["sha256"]:
            raise ValueError("Candidate hashes differ between evaluations")
    evidence = {"baseline_sha256": manifest["sha256"], "vm": live,
        "capture_validation": capture, "transfer_integrity": integrity,
        "api_probe": api_probe, "native_2018": native, "transfer": transfer}
    reports = ROOT / "ai/reports"
    (reports / "live_cic_comparison.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
    lines = ["# CIC follow-up and controlled VM validation", "",
        "Measurements: 31 October 2026; final review: 1 November 2026.", "",
        "**Keep the existing CIC-IDS2017 Random Forest deployment.** No tested newer-source candidate establishes a better general replacement. This is a limited decision about these inputs and experiments, not a ranking of complete datasets or all attack detectors.", "",
        "The selected model detects this lab's port-scan attempts, but does not identify the bounded HTTP/UDP load scenarios. It also transfers poorly to the held-out 2018 Hulk capture. A larger year number does not solve domain shift or missing temporal context.", "",
        "## What actually ran", "",
        f"- {len(live['models'])} frozen candidates were evaluated on the same saved VM records and six offline targets. This includes the original CIC/TON classifiers and anomaly detectors, UWF/CTU/mixed-source candidates, and 54 new 2018 candidates.",
        "- New training compares Random Forest, Logistic Regression and Isolation Forest, each with seeds 42/43/44, original connection features, derived ratios/rates, and directional history indicators.",
        "- Seeds vary estimator initialization while holdouts stay fixed; they are not three independent network populations or a confidence interval.",
        "- Five numeric and three categorical raw fields remain the common contract. Richer variants add derived fields and history; no IPs, ports, UIDs, absolute times or labels are model predictors. Ports/time are used only for collection, splitting and ground-truth attribution.",
        "- Existing models and thresholds were frozen. New thresholds use the 99th percentile of benign validation scores, never the VM test. Isolation Forest trains only on benign data; its anomaly flags are not confirmed attacks.",
        "- No new candidate was deployed. No automatic analysis, blocking or continuous model learning was added.", "",
        "## Sources and access limits", "",
        "| Source | Examined / measured | Limitation |", "|---|---|---|",
        "| CIC-IDS2017 | Existing labelled Zeek derivative; frozen reference holdout | Its exact extraction version and label implementation remain unverified; see the earlier extension report. |",
        "| CSE-CIC-IDS2018 | Nine original AWS archive members: server plus two Windows clients on each of 14/15/16 February; independently processed with Zeek 9.0.0 | A bounded subset, not the full dataset. Four retained attack families: SSH brute force, GoldenEye, Slowloris, Hulk. No claim about its unsampled DDoS, botnet, infiltration or web-attack days. |",
        "| CIC-DDoS2019 | Five small PCAPs attributed to it in Zenodo record 17121740; 18,386 Zeek records | A third-party derivative, not independently matched against the original release. SYN/DNS captures span less than one second; UDP-Lag spans inconsistent dates. Labels come from the declared file category plus attacker/victim pairs. Used only for exploratory frozen transfer, not new training. |",
        "| CICIoT2023 | Official description, structure and access checked | Raw download is form-gated. Published aggregate features are not interchangeable with Zeek connections. No training or measured score is claimed. |",
        "| Other newer CIC releases | Catalog and relevant descriptions reviewed: CICEV2023, CIC-UNSW-NB15 2024, medical/vehicle/industrial IoT releases and CIC-YNU-IoTMal 2026 | Specialized domains or re-extracted/processed data, not annual replacements for general IDS traffic. Their Zeek compatibility and transfer were not experimentally established here. |", "",
        "Primary sources: [CIC catalog](https://www.unb.ca/cic/datasets/index.html), [2018 description](https://www.unb.ca/cic/datasets/ids-2018.html), [AWS source](https://registry.opendata.aws/cse-cic-ids2018/), [2019 description](https://www.unb.ca/cic/datasets/ddos-2019.html), [derivative record](https://zenodo.org/records/17121740), [IoT2023 description](https://www.unb.ca/cic/datasets/iotdataset-2023.html), [CICEV](https://www.unb.ca/cic/datasets/cicev2023.html), [CIC-UNSW](https://www.unb.ca/cic/datasets/cic-unsw-nb15.html), [IoTMal2026](https://www.unb.ca/cic/datasets/ynu-iot-2026.html).", "",
        "## 2018 preparation and evaluation", "",
        "Only selected ZIP members were downloaded with HTTP ranges; publisher ZIP CRCs, ETags and local SHA256s are recorded. Original files remain unchanged locally. Two original classic PCAPs have incomplete terminal records (307 and 65 bytes); separate complete-record copies were processed. The Friday file is PCAPNG.", "",
        "A symmetric TCP cohort is selected with `not tcp or (((tcp[0:2] >> 1) + (tcp[2:2] >> 1)) & 15) = 0`. Both directions satisfy the same condition. Ignoring the least-significant port bit avoids excluding entire odd-port services when Linux clients allocate even ports. This is a deterministic port cohort, not proof of a random or representative sample of the complete dataset. Non-TCP traffic is retained. Per-capture/family hash-priority sampling then caps retained rows at 60,000 without oversampling.", "",
        "Filtering is an explicit offline tcpdump stage. The inspected Zeek build logged `-f` as installed on PCAPNG but emitted unselected tuples; preparation now rejects a cohort violation. Transferred logs are SHA256-checked against the guest to avoid incomplete or stale copies.", "",
        "Labels conservatively adapt [CNS2022's documented UTC rules](https://intrusion-detection.distrinet-research.be/CNS2022/CSECICIDS2018.html) to Zeek fields. Closed FTP attempts, zero-payload attempts, selected GoldenEye reset artefacts and unresolved attack-host traffic are excluded. This is not a reproduction of the corrected CICFlowMeter labeller: byte/state definitions and long-connection boundaries differ. Unmatched background is assumed benign, so unrelated scans or other unlabelled activity may contaminate that class.", "",
        "The final prepared subset has 74,221 rows: 6,605 assumed benign, 60,000 Hulk, 5,886 SSH brute force, 1,413 GoldenEye and 317 Slowloris. Hulk was downsampled from 112,519 retained-cohort records. These counts must not be presented as the complete 2018 distribution.", "",
        "Two protocols are separate: (1) within each capture/family, earlier 60% train, next 20% validate, last 20% test, with a 60-second connection-end purge; this is a same-campaign diagnostic with correlated endpoints, not unseen-campaign evidence; (2) whole days: Wednesday train, Thursday calibrate, Friday test. The latter tests a new Hulk campaign after training on SSH traffic. Validation attack labels do not tune the threshold. Long connections crossing day boundaries are purged.", "",
        "The original CIC reference stays on its seed-42 partition. Evaluations that would overlap an original seed-43/44 training set, or mix the two different 2018 holdouts, are marked unsupported rather than scored. None of the models is trained on the VM traces.", "",
        "Native 2018 results below use seed 42; all seeds, thresholds and confusion matrices are in the companion JSON. FPR = FP/(FP+TN).", "",
        "| Protocol | Inputs | Algorithm | Precision | Recall | F1 | FPR |", "|---|---|---|---:|---:|---:|---:|"]
    for source, report in native.items():
        for feature in ("core", "derived", "history"):
            for kind in ("random_forest", "logistic_regression", "isolation_forest"):
                result = report["models"][f"{source}-{feature}-{kind}-42"]["test"]
                lines.append("| " + " | ".join(["whole day" if "capture_day" in source else "within campaign", feature, kind,
                    *[percent(result[field]) for field in ("precision", "recall", "f1", "false_positive_rate")]]) + " |")
    lines += ["", "## Frozen cross-source transfer", "",
        "Each cell is recall / FPR on exactly the same target rows. `n/a` means training overlap would make the comparison invalid. Native-source success is not independent evidence of deployment quality.", "",
        "| Candidate (seed 42) | CIC2017 | UWF | CTU | 2018 within | 2018 day | 2019 derivative |", "|---|---|---|---|---|---|---|"]
    selected = ["deployed-cic2017", "cic2018-core-random_forest-42", "cic2018-core-logistic_regression-42",
        "cic2018-capture_day-core-random_forest-42", "cic2018-capture_day-history-logistic_regression-42"]
    for name in selected:
        cells = []
        for target in ("cic", "uwf", "ctu", "cic2018", "cic2018_day", "cic2019"):
            result = transfer["models"][name]["targets"][target]
            cells.append("n/a" if "unsupported" in result else percent(result["recall"]) + " / " + percent(result["false_positive_rate"]))
        lines.append("| " + " | ".join([name, *cells]) + " |")
    lines += ["", "## Real VM traffic and capture quality", "",
        "Windows VM 192.168.50.2 generated traffic through Ubuntu 192.168.50.1. Three controlled rounds used local HTTP downloads, UDP echo, bounded closed-port reconnaissance, repeated HTTP requests and UDP bursts. There were also 45 ordinary HTTPS requests to example.com, python.org and wikipedia.org. No public attack traffic, malware execution or distributed denial of service was generated; service exhaustion was not demonstrated.", "",
        "The initial diagnostic trace was excluded from primary model selection: Ubuntu transmit offloading caused Zeek to miss the local server's response direction despite reporting zero missed bytes. TX/TSO/GSO/GRO were temporarily disabled on enp0s8 and the complete experiment repeated with checksum validation still enabled. Original offload flags were restored exactly after that benchmark. Permanent capture preparation was added subsequently, as described below.", "",
        "The corrected capture contains 37,246 packets and reports zero tcpdump/kernel and Zeek packet drops. Of 2,013 initiated sockets, 2,012 are attributed unambiguously: 284 benign, 768 scan attempts, 900 HTTP-load sockets and 60 UDP-burst sockets. One failed benign attempt has no attributable emitted record and is excluded, not silently counted as normal. Two benign requests failed at the client; any observed records remain benign. Guest clocks differed by up to 54.32 seconds, so unique socket tuples and a bounded experiment-time window establish attribution; 3,382 background records are not assigned ground truth.", "",
        "An independent offline extraction with checksum validation agrees on all byte/packet counters, service and connection state for 2,008 common records. Four durations differ beyond 10 microseconds; four other records have no exact rounded-time match. This validates the measured common records, not every possible Zeek policy/version or production traffic condition.", "",
        "The actual backend `AnalysisEngine` validates and analyzes the same 2,012 connections in batches: 768 findings, with exactly the same connection IDs as direct baseline inference. This probe does not open the application database or exercise persistence through the analysis HTTP route. After restart, authenticated API health and sensor-status probes also succeed. No data import, analysis trigger or database clear was issued. Normal API startup applied the already-present JWT-revocation migration, and the probe session was logged out.", "",
        "After verification, 41 temporary PCAP replicas on Ubuntu were removed only after matching an allowlisted SHA256 of a copy retained on the Windows host. This freed 10,589,205,411 bytes. Actual Zeek logs, services and host-side source datasets remain; no unknown capture was removed. Temporary memory-balloon settings were reset.", "",
        "Below, scan/load columns are scenario alert coverage. A load label expresses controlled intent; it is not a confirmed attack verdict. Combined lab precision/recall/F1 in JSON refer to these scenario labels and must not be advertised as general attack-detection performance.", "",
        "| Candidate (seed 42) | Benign FPR (284 sockets) | Scan coverage | HTTP-load coverage | UDP-burst coverage |", "|---|---:|---:|---:|---:|"]
    vm_names = ["deployed-cic2017", "ton-random_forest-42", "uwf-core-random_forest-endpoint_pairs-42",
        "ctu-core-random_forest-endpoint_pairs-42", "mixed-cic-uwf-ctu-core-random_forest-endpoint_pairs-42",
        "cic2018-core-random_forest-42", "cic2018-core-logistic_regression-42", "cic2018-core-isolation_forest-42",
        "cic2018-capture_day-core-random_forest-42", "cic2018-capture_day-history-logistic_regression-42"]
    for name in vm_names:
        result = live["models"][name]["initiated_sockets"]
        lines.append("| " + " | ".join([name, percent(result["false_positive_rate"]),
            *[percent(result["per_family"][family]["alert_rate"]) for family in ("port_scan", "http_load", "udp_burst")]]) + " |")
    lines += ["", "Seed sensitivity matters: TON Random Forest has 0.35%, 9.51%, 0.35% benign FPR across seeds 42/43/44 on this same trace. The within-campaign 2018 core Random Forest has 78.52% for all three seeds; UWF core Random Forest has 31.34% for all three. Mixed core Random Forest ties the baseline's 0% benign FPR and 100% scan coverage here, but does not add load coverage and previously failed a CTU device-shift diagnostic. This trace does not justify replacing the baseline with it.", "",
        "## Decision, resources and remaining limits", "",
        "Keep CIC2017 Random Forest as the current tested baseline, while treating all findings as review signals. The 2018 forest's near-perfect native result collapses on fresh VM normal traffic; richer 2018 Logistic Regression can identify held-out Hulk but also overflags VM normal HTTP/HTTPS. No tested replacement solves the important load-context blind spot without unacceptable tradeoffs. This does not establish CIC2017 as the best complete dataset or prove that every future 2018 mixture would fail.", "",
        "The current classifier examines completed connections independently. Request/connection counts over time, destination concentration and multi-source coordination are absent. Dataset replacement alone cannot make it reliably identify distributed or repeated activity that looks ordinary per connection. Investigate explicit temporal features with separate labelled campaigns and an untouched later VM session; joint CIC2017/2018 training was not tested here.", "",
        "The measurements used this 16 GB Windows host, CPU-only, with two 4 GB VMs during capture. Numerical training ran after Windows VM shutdown; fitting uses at most two CPU workers, and inference uses one forest worker for deterministic summation. Bounded subsets and serial candidates avoid loading complete daily archives into memory. This was not a saturation, production throughput or long-duration false-alarm benchmark. Nine small-data Isolation Forest fits use all 1,834 benign Wednesday training rows because that is below the 2,048 requested sample cap; sklearn explicitly warned about the effective cap.", "",
        f"The selected compressed artifact is 1,736,913 bytes. Its recorded direct scoring call took {live['models']['deployed-cic2017']['inference_ms']:.1f} ms for 2,012 records, including the scoring wrapper; this single measurement under experiment load is not a latency guarantee. Per-candidate fit and inference times are preserved in JSON.", "",
        "Zero alarms on 284 correlated benign connections is not a zero-risk estimate. The sample is small, mostly scripted, limited to one client/gateway and a few services/sites, and all candidates share it. Offline source labels and sampling introduce uncertainty; 2018's source, label adaptation and extraction version differ from the earlier CIC derivative, so changes cannot be attributed purely to dataset age. A later independent lab session, realistic benign workloads and genuinely controlled attack scenarios remain necessary before choosing a new model.", "",
        "## Capture deployment follow-up (1 November 2026)", "",
        "The updated `sensor_agent/setup_zeek_autostart.sh` installs `/usr/local/sbin/nids-zeek-capture` and invokes it through `zeek.service` ExecStartPre. It disables and verifies TX checksum offloading, TSO, GSO, GRO and LRO on enp0s8 before every start. The interface device is a startup dependency. Zeek policies, checksum validation, NAT, forwarding and interface addresses are unchanged. The old unit is backed up before replacement; `install_zeek.sh` includes ethtool for future installations.", "",
        "Applied on Ubuntu and verified after an actual reboot: Zeek and the sensor service start automatically, all five offload features remain off, and the journal confirms capture preparation precedes ZeekControl startup. A healthy setup rerun preserves the existing Zeek PID. This permanent setup change is separate from the already-recorded benchmark measurements and does not change the selected model.", "",
        "## Files and reproduction", "",
        "Training/data preparation are separate from inference. New workflow files: `ai/cic_acquire.py`, `remote_zip.py`, `pcap_extract.py`, `cic_followup.py`, `followup_compare.py`, `live_study.py`, `lab_server.py`, `lab_client.ps1`, `lab_https_client.ps1`, and `followup_report.py`. `api/tests/unit/test_followup_contracts.py` covers attribution, clock skew, tuple ambiguity, retries, label exclusions and PCAP boundaries using synthetic inputs. No frontend files or tests were added. Dataset/model artifacts remain ignored under `.ai-workspace/`; the selected deployment SHA256 is unchanged.", "",
        "Use the pinned backend/AI Python environment. From the repository root:", "", "```powershell",
        "& api/.venv/Scripts/python.exe -m ai.cic_acquire cic2018",
        "& api/.venv/Scripts/python.exe -m ai.cic_acquire cic2019",
        "# Copy raw captures and ai/pcap_extract.py to the Ubuntu VM; extraction commands below.",
        "# Copy each conn.log and extraction.json back to fresh destinations, verify guest SHA256s.",
        "& api/.venv/Scripts/python.exe -m ai.cic_followup prepare cic2018",
        "& api/.venv/Scripts/python.exe -m ai.cic_followup prepare cic2019",
        "& api/.venv/Scripts/python.exe -m ai.cic_followup train cic2018",
        "& api/.venv/Scripts/python.exe -m ai.cic_followup train cic2018 --protocol capture_day",
        "& api/.venv/Scripts/python.exe -m ai.followup_compare --targets cic uwf ctu cic2018 cic2018_day cic2019",
        "& api/.venv/Scripts/python.exe -m ai.live_study evaluate --input .ai-workspace/live-study/corrected/sensor.jsonl --manifest .ai-workspace/live-study/corrected-manifest.json --out .ai-workspace/live-study/corrected/results.json",
        "& api/.venv/Scripts/python.exe -m ai.followup_report",
        "& api/.venv/Scripts/python.exe -m pytest api/tests/unit -q", "```", "",
        "Original reference candidates/prepared tables are prerequisites; reproduce them using the original and extension workflows in `ai/README.md`. `train cic2019` intentionally rejects the sub-second captures instead of inventing an independent holdout. Candidate binaries are local trusted training outputs; never load arbitrary downloaded joblib files.", "",
        "In Ubuntu, for each 2018 capture ID (`wed`, `thu`, `fri`, and each day's `-client-a` / `-client-b`), run the following with actual source/output paths. All processing is offline; no live service is restarted:", "", "```bash",
        "python3 extract.py SOURCE.pcap --out ID-cohort-v2 --filter 'not tcp or (((tcp[0:2] >> 1) + (tcp[2:2] >> 1)) & 15) = 0'",
        "# For each 2019 derivative file, use a distinct output directory and omit --filter.",
        "python3 extract.py SOURCE.pcap --out SOURCE-zeek", "```", "",
        "Place 2018 outputs at `.ai-workspace/live-study/cic2018/zeek-cohort-v2/ID.conn.jsonl` and `ID.extraction.json`; 2019 outputs use `cic2019/Benign.conn.jsonl`, `DNS.conn.jsonl`, `SynFlood.conn.jsonl`, `UDPLag.conn.jsonl`, `WebDDoS.conn.jsonl`. Raw downloads and per-capture fingerprints are in each source's `sources.json`. Full VM captures and manifests stay in the ignored workspace, not the published report. Live traffic cannot be regenerated byte-identically; evaluation of the saved trace is reproducible.", "",
        "To collect another lab run, use an isolated private lab only: run `lab_server.py` as root on Ubuntu with explicit bind/client/interface, a fresh output directory and `--seconds 900`; run the two PowerShell clients inside Windows VM with explicit output paths; combine their manifests. Wait for Zeek's connection flush before `ai.live_study fetch --env-file .env --out NEW_DIRECTORY`. Record original offload flags, ensure valid capture counters/responses, and restore temporary flags afterward. Do not disable live checksum validation as a shortcut. The diagnostic traces from before correction are not selection evidence.", "",
        "Verification: 235 backend unit tests passed (four existing Pydantic deprecation warnings); both PowerShell scripts parsed without errors; all 15 transferred final guest logs matched SHA256; corrected capture dropped zero packets; the runtime engine agreed with frozen baseline inference. No branch, staging, commit or push was performed.", ""]
    (reports / "live_cic_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Published {len(live['models'])} candidates and six offline targets")


if __name__ == "__main__":
    main()
