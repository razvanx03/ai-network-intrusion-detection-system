# Measured connection classifier comparison

Report generated 2026-10-22. Binary labels: benign=0, attack=1. All values below come from executed local runs.
No VM experiment or raw-PCAP re-extraction was performed locally. See ../README.md for the full protocol and reproduction commands.

## Data audit

| Dataset | Raw rows | Exact duplicates removed | Remaining rows | Endpoint-pair groups | Timestamps |
|---|---:|---:|---:|---:|---|
| ton | 211,043 | 20,569 | 190,474 | 1,004 | False |
| cic | 3,239,594 | 1,120,412 | 2,119,182 | 61,979 | True |

TON uses a version-pinned community network subset, not the complete raw collection. CIC uses a published five-day Zeek derivative, not CICFlowMeter CSVs or CNS2022 corrected labels. Hashes and provenance are in comparison.json.
The CIC derivative's exact Zeek version and full label implementation are unverified. Capture gaps and weak annotation remain potential confounders. Source confidence/evidence fields are never inputs.

## Comparable grouped runs: mean over seeds 42, 43, 44

Unweighted means across three different endpoint-pair partitions; no confidence interval is claimed. The held-out attack prevalence and family coverage differ across datasets and seeds. These means include previously absent attack families; they are not purely known-attack scores.

| Dataset | Model | Precision | Recall | F1 | FPR | Recall range |
|---|---|---:|---:|---:|---:|---|
| ton | logistic_regression | 99.20% | 54.81% | 62.26% | 1.55% | 6.42% - 92.21% |
| ton | random_forest | 99.35% | 93.36% | 96.13% | 1.49% | 84.66% - 99.12% |
| ton | isolation_forest | 50.58% | 0.35% | 0.70% | 1.27% | 0.15% - 0.74% |
| cic | logistic_regression | 91.56% | 68.18% | 76.05% | 2.09% | 42.59% - 89.75% |
| cic | random_forest | 94.98% | 76.09% | 81.98% | 1.97% | 41.84% - 95.17% |
| cic | isolation_forest | 36.17% | 2.58% | 4.72% | 1.90% | 1.48% - 3.79% |

Thresholds target 1% FPR on benign validation records only. This does not guarantee 1% held-out FPR. No threshold tuning uses held-out data.

## All individual runs and confusion matrices

Matrix format: [[TN, FP], [FN, TP]]. For Isolation Forest, 'attack' in this scoring table is the ground-truth evaluation target; its own output is only an unusualness score.

| Dataset / protocol / seed | Model | Precision | Recall | F1 | FPR | Confusion matrix |
|---|---|---:|---:|---:|---:|---|
| cic-endpoint_pairs-42 | logistic_regression | 88.07% | 89.75% | 88.90% | 0.86% | `[[37047, 320], [270, 2363]]` |
| cic-endpoint_pairs-42 | random_forest | 95.17% | 91.26% | 93.18% | 0.33% | `[[37245, 122], [230, 2403]]` |
| cic-endpoint_pairs-42 | isolation_forest | 10.08% | 1.48% | 2.58% | 0.93% | `[[37019, 348], [2594, 39]]` |
| cic-endpoint_pairs-43 | logistic_regression | 90.07% | 72.20% | 80.15% | 1.91% | `[[31658, 615], [2148, 5578]]` |
| cic-endpoint_pairs-43 | random_forest | 93.85% | 95.17% | 94.51% | 1.49% | `[[31791, 482], [373, 7353]]` |
| cic-endpoint_pairs-43 | isolation_forest | 18.45% | 2.46% | 4.34% | 2.60% | `[[31433, 840], [7536, 190]]` |
| cic-endpoint_pairs-44 | logistic_regression | 96.55% | 42.59% | 59.11% | 3.49% | `[[11708, 424], [15995, 11868]]` |
| cic-endpoint_pairs-44 | random_forest | 95.92% | 41.84% | 58.26% | 4.09% | `[[11636, 496], [16206, 11657]]` |
| cic-endpoint_pairs-44 | isolation_forest | 80.00% | 3.79% | 7.24% | 2.18% | `[[11868, 264], [26807, 1056]]` |
| cic-within_scenario_time-42 | logistic_regression | 97.98% | 52.75% | 68.58% | 0.36% | `[[29977, 108], [4683, 5228]]` |
| cic-within_scenario_time-42 | random_forest | 99.11% | 93.60% | 96.28% | 0.28% | `[[30002, 83], [634, 9277]]` |
| cic-within_scenario_time-42 | isolation_forest | 67.20% | 4.24% | 7.97% | 0.68% | `[[29880, 205], [9491, 420]]` |
| ton-endpoint_pairs-42 | logistic_regression | 99.55% | 92.21% | 95.74% | 2.96% | `[[3966, 121], [2239, 26504]]` |
| ton-endpoint_pairs-42 | random_forest | 99.87% | 96.29% | 98.05% | 0.91% | `[[4050, 37], [1066, 27677]]` |
| ton-endpoint_pairs-42 | isolation_forest | 68.61% | 0.74% | 1.46% | 2.37% | `[[3990, 97], [28531, 212]]` |
| ton-endpoint_pairs-43 | logistic_regression | 98.75% | 65.81% | 78.98% | 1.54% | `[[13766, 216], [8895, 17118]]` |
| ton-endpoint_pairs-43 | random_forest | 98.36% | 99.12% | 98.74% | 3.08% | `[[13552, 430], [229, 25784]]` |
| ton-endpoint_pairs-43 | isolation_forest | 19.80% | 0.15% | 0.30% | 1.13% | `[[13824, 158], [25974, 39]]` |
| ton-endpoint_pairs-44 | logistic_regression | 99.31% | 6.42% | 12.06% | 0.14% | `[[7298, 10], [21084, 1447]]` |
| ton-endpoint_pairs-44 | random_forest | 99.81% | 84.66% | 91.61% | 0.49% | `[[7272, 36], [3456, 19075]]` |
| ton-endpoint_pairs-44 | isolation_forest | 63.33% | 0.17% | 0.34% | 0.30% | `[[7286, 22], [22493, 38]]` |

The CIC within-scenario-time supplement splits each family's timeline, purges connections crossing boundaries and adds a 60-second embargo. It still shares campaigns and endpoints; it is not evidence from independent future attacks. TON has no timestamps in this subset, so no equivalent temporal score exists.

## Frozen cross-dataset transfer

No target refitting, target preprocessing fit or target threshold tuning. Different label families make these stress evaluations rather than matched attack comparisons.

| Source -> target / seed | Model | Precision | Recall | F1 | FPR |
|---|---|---:|---:|---:|---:|
| ton -> cic / 42 | logistic_regression | 26.36% | 98.52% | 41.59% | 19.40% |
| ton -> cic / 42 | random_forest | 9.74% | 96.13% | 17.69% | 62.75% |
| ton -> cic / 42 | isolation_forest | 0.95% | 0.80% | 0.87% | 5.84% |
| cic -> ton / 42 | logistic_regression | 87.05% | 38.94% | 53.81% | 40.74% |
| cic -> ton / 42 | random_forest | 99.99% | 47.88% | 64.75% | 0.02% |
| cic -> ton / 42 | isolation_forest | 5.95% | 0.06% | 0.11% | 6.19% |
| ton -> cic / 43 | logistic_regression | 44.36% | 65.34% | 52.84% | 19.62% |
| ton -> cic / 43 | random_forest | 24.26% | 80.27% | 37.26% | 60.00% |
| ton -> cic / 43 | isolation_forest | 1.17% | 0.44% | 0.64% | 8.87% |
| cic -> ton / 43 | logistic_regression | 99.90% | 34.08% | 50.83% | 0.06% |
| cic -> ton / 43 | random_forest | 99.94% | 18.13% | 30.69% | 0.02% |
| cic -> ton / 43 | isolation_forest | 1.57% | 0.05% | 0.10% | 6.28% |
| ton -> cic / 44 | logistic_regression | 91.83% | 35.64% | 51.35% | 7.29% |
| ton -> cic / 44 | random_forest | 89.59% | 39.64% | 54.96% | 10.58% |
| ton -> cic / 44 | isolation_forest | 80.36% | 6.05% | 11.25% | 3.40% |
| cic -> ton / 44 | logistic_regression | 86.60% | 24.24% | 37.87% | 11.56% |
| cic -> ton / 44 | random_forest | 73.23% | 27.46% | 39.95% | 30.95% |
| cic -> ton / 44 | isolation_forest | 2.63% | 0.13% | 0.25% | 15.22% |

## Selection and scope

The initial deployment uses the CIC grouped reference run (seed 42), Random Forest, with its unchanged validation-calibrated threshold. Seed 42 was the fixed reference, not the best held-out seed. Mean validation recall across the three partitions is:

| Dataset | Model | Mean validation recall |
|---|---|---:|
| ton | logistic_regression | 62.52% |
| ton | random_forest | 90.55% |
| cic | logistic_regression | 49.25% |
| cic | random_forest | 92.64% |

Reasons: a shared Zeek feature contract; a broader workstation/service background in CIC; strong Random Forest validation results at the chosen FPR budget; very high TON-to-CIC false alarms; and small inference artifacts. TON's higher internal F1 is not treated as proof of better applicability.
CIC is the better initial baseline for this application, not a validated deployment-quality detector. CIC seed 44 exposes a major limitation: entire attack families move outside training and recall falls sharply. Cross-domain scores likewise do not establish generalization. Both datasets remain useful; neither replaces controlled local validation.
Isolation Forest has very low attack recall at the selected operating points. It remains an offline anomaly experiment and is not activated. No combined classifier/anomaly system is claimed.
The deployed binary model emits only Suspicious Connection findings requiring review. It does not identify specific attack families, certify anomalies as attacks, or provide calibrated attack probabilities. The absence of a finding is not proof of safety.

## Selected run: family coverage

| Family | Training support | Held-out support | Binary detection rate |
|---|---:|---:|---:|
| benign | 55086 | 37367 | 0.33% |
| botnet_ares | 76 | 192 | 82.81% |
| ddos_loic | 4845 | 0 | not evaluated |
| dos_goldeneye | 396 | 0 | not evaluated |
| dos_hulk | 7926 | 0 | not evaluated |
| dos_slowhttptest | 815 | 0 | not evaluated |
| dos_slowloris | 197 | 0 | not evaluated |
| ftp_patator | 201 | 0 | not evaluated |
| heartbleed | 0 | 1 | 0.00% |
| portscan | 10317 | 2440 | 91.97% |
| ssh_patator | 126 | 0 | not evaluated |
| web_bruteforce | 7 | 0 | not evaluated |
| web_sql_injection | 1 | 0 | not evaluated |
| web_xss | 1 | 0 | not evaluated |

The benign row is a false-positive rate. One or a few records never establish attack-category performance. Detailed results for known-family-only and distinct-feature-vector sensitivity are in comparison.json.

## Resources

- Selected compressed artifact: 1,736,913 bytes.
- Model load in a fresh process: 0.211 seconds.
- Median prediction time for 500 prepared records: 28.05 ms.
- Peak process RSS including imports, model and held-out table: 272.0 MiB.
- Host CPU measurements only; no claim of measured laptop performance or combined VM/application memory consumption.

## Executed verification

- 200 real held-out records were normalized and saved in a separate temporary SQLite database.
- Offline/DTO/stored feature parity verified; manual API analysis persisted 94 findings, matching direct classifier predictions.
- Cookie login, unauthorized access refusal, detector health, session completion, evidence links and logout verified through ASGI requests.
- Missing values initially changed through ORM zero defaults; corrected normalization/storage and repeated the parity/API check successfully.
- Frontend build and lint completed; build retains a bundle-size warning. Python compilation, dependency consistency and whitespace checks completed.
- No automated test suite was added. Production database and VM configuration were not modified.

## Remaining validation

Measure benign alarm rates and controlled attack recall on the real VM path; inspect Zeek 9 checksum policy, capture loss and extractor compatibility; calibrate using independently recorded benign lab data; evaluate on untouched local holdouts and on the laptop. Do not tune repeatedly on the same holdout. More protocol/security context and meaningful behavioral windows require additional work.
