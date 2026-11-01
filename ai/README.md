# Connection AI experiments

The CIC follow-up adds independently extracted CSE-CIC-IDS2018 subsets,
an exploratory CIC-DDoS2019 derivative check, and controlled live VM validation.
See [`reports/live_cic_report.md`](reports/live_cic_report.md) for the measured
comparison, capture-quality issue, access limits, and reproduction commands;
[`reports/live_cic_comparison.json`](reports/live_cic_comparison.json) contains
all candidate metrics. The selected deployment remains unchanged. Newer source
dates alone do not establish better transfer or reliable load detection.

The source/feature extension study compares the existing CIC baseline with
official UWF-ZeekData24 partitions and a selected CTU-SME-11 subset. See
[`reports/extension_report.md`](reports/extension_report.md) for measured results,
selection limits and reproduction commands. `study_acquire.py`,
`study_prepare.py`, `study_experiment.py` and `study_report.py` implement this
separate offline workflow. Its downloads and candidate models stay under the
Git-ignored `.ai-workspace/extension/`; none is automatically deployed.

The study separates source changes from feature changes: original connection
inputs, derived ratios/rates, and directional Zeek history indicators. Frozen
cross-source holdouts, whole-day diagnostics and a CTU device-holdout check
challenge native-dataset scores. The current runtime feature contract remains
unchanged unless a candidate is explicitly selected and integrated.

Offline preparation and training live in `ai/`. Shared feature extraction and
inference live in `api/app/ai/`. No training, downloading, ingestion or scheduled
analysis is triggered by starting the API. Inference still requires the existing
manual analysis command.

## Reproduce from the repository root

Use Python 3.13 (the recorded run used 3.13.14) and a virtual environment. The
PowerShell commands below use the existing backend environment:

```powershell
& api/.venv/Scripts/python.exe -m pip install -r api/requirements.txt -r ai/requirements.txt
& api/.venv/Scripts/python.exe -m ai.acquire
& api/.venv/Scripts/python.exe -m ai.prepare
& api/.venv/Scripts/python.exe -m ai.experiment --seeds 42 43 44 --temporal
& api/.venv/Scripts/python.exe -m ai.compare
```

On Linux, substitute the environment's `bin/python`. Initial acquisition requires
network access. Downloads are hash checked and cached under `.ai-workspace/`,
which is excluded from Git. A missing source, malformed table, invalid numerical
value or checksum mismatch fails explicitly. Data is never replaced with mock
traffic. No downloaded executable, notebook or model is run.

The recorded sources total about 141 MB. Prepared tables and run artifacts consume
additional disk space. The scripts load one source or prepared dataset at a time;
model fitting is capped at 80,000 records, validation at 20,000 and evaluation at
40,000 per run. Random Forest and Isolation Forest use two CPU workers and 120
trees. Native numerical thread pools are bounded during fitting. No GPU is used.

## Sources and provenance

- TON_IoT Network: [original description](https://research.unsw.edu.au/projects/toniot-datasets).
  The original download redirected to sign-in during acquisition. The recorded
  `train_test_network.csv` is a community mirror at
  [codymlewis/TON_IoT_network](https://huggingface.co/datasets/codymlewis/TON_IoT_network),
  revision `b953d9388d2db3bc392ea7150476e4f219a2a1cb`. SHA256 is pinned in
  `acquire.py`. This verifies the downloaded mirror, not identity against an
  independently obtained original. The subset has no timestamps or source capture
  identifiers. It includes nine labelled attack categories plus normal traffic.
- CIC-IDS2017: [original description](https://www.unb.ca/cic/datasets/ids-2017.html).
  The experiment uses the separately published **Zeek flows extracted from ISCX
  IDS 2017 Dataset**, version 1.0, [DOI 10.5281/zenodo.21469685](https://doi.org/10.5281/zenodo.21469685).
  All five daily Parquet files are downloaded, along with their summary and
  metadata. Publisher MD5 checksums are verified; SHA256 values are recorded too.
  These are Zeek re-extractions from the original PCAPs, not renamed CICFlowMeter
  features. Raw PCAP retrieval was investigated but the legacy addresses returned
  HTML and the current download page was form gated. We did not independently
  reprocess the raw captures. The derivative description says checksum checking
  was disabled; its exact Zeek version and complete extraction/label code are not
  supplied in the record. It does not establish Zeek 9 equivalence.

Source label limitations remain: both are controlled environments, not a guarantee
of coverage in another network. The TON_IoT environment includes IoT/IIoT systems;
its normality is not interchangeable with workstation/service traffic. CIC's
derivative labels are a separate annotation scheme, not the corrected CNS2022
labels. Original CIC issues are documented in
[CNS2022](https://intrusion-detection.distrinet-research.be/CNS2022/index.html).
Neither its corrected labels nor its `Attempted` handling have been imported or
claimed here. The Parquet files contain label confidence/evidence/rule fields;
these are audited but never classifier inputs. Weak labels and incomplete
background truth can bias all reported metrics.

Review source terms before redistribution. TON_IoT commercial reuse requires
author permission under the published terms. The selected CIC derivative record
declares CC BY 4.0. Attribute the original dataset authors and the derivative
creators when sharing results or trained artifacts. Downloaded traffic is not
included in the model export.

## Feature contract

`zeek-conn-core-v1` has five nonnegative numerical fields: `duration`, `orig_bytes`,
`resp_bytes`, `orig_pkts`, `resp_pkts`; and three categorical fields: `proto`,
`service`, `conn_state`. Each numerical field becomes `log1p(value)` plus a missing
indicator. Missing values are imputed to zero only after recording missingness.
Categories are normalized to lowercase, with explicit `unknown`; encoders and
scalers are fitted exclusively on training rows. Previously unseen categories are
handled by the fitted encoder's explicit ignore policy.

TON mappings are `src_bytes -> orig_bytes`, `dst_bytes -> resp_bytes`,
`src_pkts -> orig_pkts`, `dst_pkts -> resp_pkts`. The source definitions describe
Zeek payload/sequence bytes and originator/responder packet counts. Those mappings
are not equivalent to arbitrary IP byte totals or Argus/CICFlowMeter counters.
The CIC derivative uses the standard Zeek names. Exact Zeek-version behavior,
timeouts, capture loss and checksum policies remain compatibility limitations.

No IPs, UID, ports, absolute timestamps, capture names, labels, rule IDs, label
confidence, DNS/HTTP/TLS fields or Zeek `history` enter the models. Thus only core
connection features available in both sources and the application are compared.
The API preserves missing numerical values through normalization **and storage**;
existing zero values previously saved in the database cannot be reconstructed.
The preparation version changes to `zeek-connection-v2` for traceability.

Connection payload totals, IP byte totals, packet flags and window statistics are
not interchangeable. Zeek `history` cannot reconstruct exact TCP flag counts.
No packet-level IAT, jitter, TTL, packet-length distribution or time-window
behavior is claimed. No DNS/HTTP/TLS ingestion was added.

## Evaluation protocol

1. Remove exact full-source-row duplicates before splitting. Audit files retain
   before/after counts. CIC has one distinct record per UID after this removal;
   the repeated rows are not independent connections.
   TON has no timestamps in this subset: identical rows cannot conclusively be
   distinguished from separate events with identical recorded attributes, so
   deduplication also changes its observed traffic distribution.
2. Group by the **unordered endpoint IP pair**. Reverse traffic between a pair
   stays in one partition. Use fixed seeds 42, 43, 44, with approximately 60%/20%/20%
   of groups for training/validation/evaluation. This does not isolate every host
   or every attack campaign. IPs are grouping metadata only and are hashed in the
   prepared tables. Splits are never retried to obtain better scores.
3. Apply bounded proportional family sampling independently inside each partition.
   Preserve available rare families without oversampling. There is no synthetic
   balancing or preprocessing fitted on held-out data.
4. Train weighted Logistic Regression (`C=1`) and weighted Random Forest
   (`max_depth=16`, `min_samples_leaf=5`). These are binary classifiers; per-family
   recall is detection of labelled traffic, not attack-family classification.
5. Fit Isolation Forest on benign training rows only. It is assessed separately;
   an unusualness score is not an attack probability or confirmation.
6. Calibrate each operating threshold on **benign validation rows only**, targeting
   at most 1% validation false positives. A conservative tie policy is used. The
   held-out FPR is measured independently and can be much larger. A 0.5 classifier
   threshold is reported separately. No threshold is fitted to held-out labels.
7. Report precision, recall, F1, FPR, confusion counts `[[TN, FP], [FN, TP]]`,
   per-family support, absent training families, and separate known-family metrics.
   Some endpoint pairs contain entire attack campaigns: group isolation can move
   a whole attack family out of training. The main grouped results therefore
   include both familiar and unfamiliar families. They are not pure known-attack
   estimates. Single-digit supports cannot support category-level conclusions.
8. Report feature-vector-overlap sensitivity and a balanced-prevalence evaluation.
   Identical feature vectors can represent independent real connections, not
   necessarily duplicated source rows. The distinct-vector sensitivity is separate
   because removing common feature vectors changes the population substantially.
   Balanced prevalence also does not make different attack families equivalent.
9. Measure transfer in both directions with frozen preprocessing, model and
   threshold. No target fitting or tuning is performed. Distributions and label
   meanings differ, so transfer measures robustness rather than a fair universal
   ranking of dataset quality.

Supplement: CIC has timestamps, so a within-family chronological 60/20/20 split is
also measured, dropping connections crossing boundaries plus a 60-second embargo.
Families with fewer than ten records are omitted in that supplement. This measures
later portions of existing scenarios, **not independent attacks**; families'
boundaries differ and there is no single global chronological cutoff. TON's
downloaded subset cannot support this experiment because timestamps are absent.
Do not pool the temporal scores into the comparable grouped averages.

## Selection, inference and transfer

See [the measured report](reports/experiment_report.md), machine-readable
`reports/comparison.json`, `reports/metrics.csv`, and `reports/runtime_resources.json`.
The initial deployment is the CIC grouped seed-42 Random Forest. Selection considers
validation results, the measured failure of TON-to-CIC transfer, feature support,
traffic scope and resources. Seed 42 is the predeclared reference run, **not the
best seed selected using evaluation scores**. No held-out records are refitted.

```powershell
& api/.venv/Scripts/python.exe -m ai.deploy --run cic-endpoint_pairs-42 --model random_forest
& api/.venv/Scripts/python.exe -m ai.benchmark
& api/.venv/Scripts/python.exe -m ai.export
& api/.venv/Scripts/python.exe -m ai.report
```

Restart the API after selection. `deployment.json` is an explicit startup
configuration. A missing artifact, wrong SHA256, schema mismatch or incompatible
dependency version fails startup; it never silently disables the selected model.
To explicitly disable inference, set `enabled` to `false` in that file.

The selected artifact is Git-ignored. A fresh checkout must reproduce the selected
run or receive `.ai-workspace/export/selected-ai-model.zip`, extracted into the
repository root. Install the pinned backend requirements in the laptop environment.
Do not load untrusted joblib/pickle artifacts: their format can execute code.
The export contains only the selected artifact, deployment manifest and backend
requirements, with no credentials, database or captured traffic.

The adapter preserves `AnalysisEngine`, manual analysis, source-record links and
per-batch transactions. It emits only **Suspicious Connection**, medium severity,
with no fabricated MITRE mapping or attack-family claim. `confidence` contains the
classifier's uncalibrated score, not a verified attack probability. Descriptions
are translated by the frontend. Isolation Forest is not deployed because these
experiments do not justify it. The absence of an alert is not proof of safety.

## Verification and remaining work

The recorded manual API check uses 200 real held-out CIC records in a separate
temporary SQLite database: compare features before/after storage, authenticate
with the existing cookie flow, trigger stored-record analysis, compare alert
counts to offline predictions, inspect source evidence links and verify logout.
It does not call the remote sensor or alter the application database. Its result
is in `reports/manual_verification.json`; this is a record of an executed manual
check, not an automated test suite.

```powershell
& api/.venv/Scripts/python.exe -m compileall -q ai api/app
& api/.venv/Scripts/python.exe -m pip check
git diff --check
cd app
npm run build
npm run lint
```

Backend unit checks are now available under `api/tests/unit/`; see the root README
for commands and isolation limits. They do not replace dataset evaluation or the
recorded API check. No branches, staging, commits or pushes are created. Live VM traffic,
capture quality, benign lab alarm rates, controlled lab attack recall, laptop
performance and additional protocol/security logs still need validation. No new
VM experiment was performed for this comparison. Train/evaluation scores do not
establish those properties.
