# Connection source and feature extension study

All numerical results below were measured locally. The deployed artifact was not replaced.

## Decision

Retain the existing CIC Random Forest. UWF-only and CTU-only training do not establish a better replacement. A bounded mixed-source forest improves coverage across the main fixed holdouts, but that advantage is not stable when CTU devices and their endpoint pairs are held out. Richer connection features do not remove that failure. No new model is integrated into runtime.
The mixed-source core forest is a useful follow-up candidate, not the new accepted model. The mixed derived profile offers a different recall/false-alarm compromise. Neither is demonstrated to improve live capture results. Extra DNS/HTTP/TLS ingestion or temporal behavior features remain possible future experiments, not measured benefits in this study.

## Protocol

- Same five numeric and three categorical Zeek fields as the deployed model; no raw IP, UID, date, port or annotation is a predictor.
- Core: 13 transformed inputs. Derived: core plus 8 ratios/rates/missingness indicators. History: derived plus 13 directional Zeek history indicators (not exact TCP flag counts).
- Random Forest and Logistic Regression use the existing estimator settings; train/validation/test caps are 80,000/20,000/40,000 records. Training/native-thread limit per process: two. Forest inference uses one worker for deterministic tree aggregation.
- Primary endpoint-pair partitions and sampling are frozen at seed 42. Estimator seeds 42/43/44 measure initialization sensitivity only. Other splits in the original study remain separate evidence.
- Additional p43/p44 challenges vary the new-domain endpoint partitions, always retaining CIC's original seed-42 partition so the deployed model never sees its own training records as test data.
- The CIC reference partition reproduces the original feature vectors, labels, groups and seed-42 metrics. The deployed model is never evaluated on a new CIC split that could contain its training rows.
- Thresholds use only benign validation scores (99th percentile plus nextafter). Mixed training uses equal per-domain training budgets and the most conservative participating-domain threshold. No held-out threshold tuning.
- Every candidate is evaluated on the same target holdouts. Cross-source precision/F1 differ with target attack prevalence; compare candidate models within a target column, not across unrelated datasets.
- Whole-day diagnostics hold CTU dates out chronologically. UWF's benign and malicious dates occupy different seasons, so its per-class date diagnostic is NOT evidence of global forward-time generalization. CIC keeps its original reference partition in this diagnostic.
- Device diagnostics train CTU models on Windows full-1 and hold out Windows AD and Echo. All endpoint pairs observed in those held-out captures are purged from CTU fitting/calibration. A fixed grouped validation split may be benign-only; threshold calibration needs benign support, not attack labels. No split seed is retried to obtain a better score.
- The device diagnostic also changes attack-family support: full-1 training contains DNS C2 connection attempts, whereas AD/Echo test traffic includes discovery, human attacks and other malware annotations. It is a joint device/campaign/family stress test, not a clean measurement of device shift alone. Family names across different sources are not assumed equivalent.
- Connection duplicates are removed before splitting. UWF secondary Duplicate annotation rows are not separate flows. Conflicting binary identities are excluded. CTU background/unknown is excluded, never silently treated as benign.
- Full metrics include confusion matrices, family support, feature-vector overlap and distinct-vector sensitivity. These are connection-review scores, not calibrated attack probabilities or proof of specific ATT&CK tactics.

## Source audit

| Source | Retained connections | Benign | Attack | Endpoint-pair groups |
|---|---:|---:|---:|---:|
| cic | 2,119,182 | 1,593,905 | 525,277 | 61,979 |
| uwf | 1,897,812 | 958,109 | 939,703 | 587 |
| ctu | 499,714 | 280,555 | 219,159 | 12,022 |

UWF: seven dated official Parquet partitions; attack captures are February/March 2024 and benign captures October/November 2024. Time is excluded from predictors, but correlated protocol/background differences can still make classification easy.
CTU: all seven days from two Windows systems (AD and full-1), plus Amazon Echo as a supplementary device. The Linux flood-dominated archive is excluded. This is a selected subset, not the entire CTU population. Archive publisher MD5 checks and local SHA-256 fingerprints are retained in the JSON report.

## Frozen deployed baseline

| Target | Precision | Recall | F1 | False-positive rate |
|---|---:|---:|---:|---:|
| cic | 95.168% | 91.265% | 93.176% | 0.326% |
| uwf | 87.888% | 1.410% | 2.775% | 0.196% |
| ctu | 89.699% | 61.815% | 73.191% | 1.514% |

## endpoint_pairs: random_forest

Each cell is attack recall / benign false-positive rate. Means across listed estimator seeds; no confidence interval is claimed.

| Training source | Inputs | Seeds | CIC | UWF | CTU |
|---|---|---|---:|---:|---:|
| cic | core | [42, 43, 44] | 91.265% / 0.326% | 0.981% / 1.479% | 62.916% / 1.804% |
| cic | derived | [42, 43, 44] | 91.290% / 0.328% | 1.656% / 4.256% | 65.159% / 2.385% |
| cic | history | [42, 43, 44] | 91.328% / 0.326% | 2.546% / 4.367% | 65.344% / 2.389% |
| ctu | core | [42, 43, 44] | 3.304% / 0.249% | 0.110% / 0.273% | 61.303% / 1.532% |
| ctu | derived | [42, 43, 44] | 2.735% / 0.249% | 0.218% / 0.107% | 61.374% / 1.511% |
| ctu | history | [42, 43, 44] | 3.228% / 0.249% | 0.013% / 0.226% | 61.322% / 1.516% |
| mixed | core | [42, 43, 44] | 92.151% / 0.555% | 93.238% / 0.050% | 68.668% / 1.529% |
| mixed | derived | [42, 43, 44] | 90.505% / 0.321% | 94.485% / 0.062% | 69.047% / 1.498% |
| mixed | history | [42, 43, 44] | 91.239% / 0.554% | 92.854% / 0.015% | 64.784% / 1.429% |
| uwf | core | [42, 43, 44] | 0.760% / 18.026% | 97.549% / 0.110% | 0.498% / 10.889% |
| uwf | derived | [42, 43, 44] | 0.253% / 4.690% | 97.536% / 0.115% | 0.285% / 5.698% |
| uwf | history | [42, 43, 44] | 1.393% / 16.235% | 96.408% / 0.072% | 1.129% / 13.684% |

## endpoint_pairs: logistic_regression

Each cell is attack recall / benign false-positive rate. Means across listed estimator seeds; no confidence interval is claimed.

| Training source | Inputs | Seeds | CIC | UWF | CTU |
|---|---|---|---:|---:|---:|
| cic | core | [42, 43, 44] | 89.746% / 0.856% | 4.728% / 4.362% | 34.628% / 2.724% |
| cic | derived | [42, 43, 44] | 91.607% / 0.476% | 6.083% / 4.392% | 33.020% / 1.231% |
| cic | history | [42, 43, 44] | 91.607% / 0.474% | 6.302% / 4.432% | 33.817% / 1.256% |
| ctu | core | [42, 43, 44] | 89.821% / 5.791% | 4.728% / 4.382% | 34.941% / 3.194% |
| ctu | derived | [42, 43, 44] | 30.573% / 0.391% | 0.000% / 0.000% | 13.473% / 0.033% |
| ctu | history | [42, 43, 44] | 30.877% / 14.181% | 1.509% / 0.130% | 22.578% / 0.088% |
| mixed | core | [42, 43, 44] | 0.038% / 0.289% | 0.164% / 0.000% | 0.028% / 1.893% |
| mixed | derived | [42, 43, 44] | 25.332% / 0.843% | 43.591% / 0.000% | 12.249% / 2.229% |
| mixed | history | [42, 43, 44] | 24.535% / 1.092% | 44.866% / 0.000% | 11.794% / 2.087% |
| uwf | core | [42, 43, 44] | 4.406% / 19.919% | 96.129% / 0.035% | 50.832% / 23.210% |
| uwf | derived | [42, 43, 44] | 4.709% / 17.232% | 96.159% / 0.035% | 41.628% / 19.570% |
| uwf | history | [42, 43, 44] | 80.972% / 14.813% | 96.154% / 0.035% | 57.917% / 17.641% |

## endpoint_pairs_p43: random_forest

Each cell is attack recall / benign false-positive rate. Means across listed estimator seeds; no confidence interval is claimed.

| Training source | Inputs | Seeds | CIC | UWF | CTU |
|---|---|---|---:|---:|---:|
| cic | core | [42] | 91.265% / 0.326% | 22.676% / 0.406% | 66.459% / 0.855% |
| ctu | core | [42] | 93.240% / 0.947% | 50.709% / 13.395% | 90.870% / 28.831% |
| mixed | core | [42] | 92.176% / 0.554% | 22.704% / 0.025% | 63.809% / 0.771% |
| uwf | core | [42] | 99.772% / 43.718% | 100.000% / 13.721% | 90.870% / 35.100% |

## endpoint_pairs_p43: logistic_regression

Each cell is attack recall / benign false-positive rate. Means across listed estimator seeds; no confidence interval is claimed.

| Training source | Inputs | Seeds | CIC | UWF | CTU |
|---|---|---|---:|---:|---:|
| cic | core | [42] | 89.746% / 0.856% | 50.737% / 13.469% | 29.843% / 1.510% |
| ctu | core | [42] | 89.366% / 1.078% | 0.028% / 0.000% | 11.747% / 0.344% |
| mixed | core | [42] | 87.505% / 1.426% | 19.076% / 0.011% | 11.616% / 0.260% |
| uwf | core | [42] | 67.452% / 23.256% | 100.000% / 13.954% | 92.016% / 28.306% |

## endpoint_pairs_p44: random_forest

Each cell is attack recall / benign false-positive rate. Means across listed estimator seeds; no confidence interval is claimed.

| Training source | Inputs | Seeds | CIC | UWF | CTU |
|---|---|---|---:|---:|---:|
| cic | core | [42] | 91.265% / 0.326% | 0.566% / 0.245% | 7.091% / 1.601% |
| ctu | core | [42] | 35.967% / 1.480% | 3.223% / 0.555% | 98.505% / 2.676% |
| mixed | core | [42] | 92.176% / 0.557% | 94.794% / 0.033% | 96.856% / 1.517% |
| uwf | core | [42] | 0.836% / 20.679% | 99.863% / 0.326% | 0.030% / 10.355% |

## endpoint_pairs_p44: logistic_regression

Each cell is attack recall / benign false-positive rate. Means across listed estimator seeds; no confidence interval is claimed.

| Training source | Inputs | Seeds | CIC | UWF | CTU |
|---|---|---|---:|---:|---:|
| cic | core | [42] | 89.746% / 0.856% | 2.538% / 5.611% | 2.357% / 2.886% |
| ctu | core | [42] | 0.000% / 0.000% | 0.000% / 0.000% | 0.000% / 0.000% |
| mixed | core | [42] | 0.038% / 0.281% | 0.018% / 0.000% | 0.003% / 0.421% |
| uwf | core | [42] | 4.330% / 18.773% | 99.971% / 0.326% | 5.720% / 29.653% |

## capture_days: random_forest

Each cell is attack recall / benign false-positive rate. Means across listed estimator seeds; no confidence interval is claimed.

| Training source | Inputs | Seeds | CIC | UWF | CTU |
|---|---|---|---:|---:|---:|
| cic | core | [42] | 91.265% / 0.326% | 1.368% / 0.126% | 73.215% / 0.000% |
| cic | derived | [42] | 91.341% / 0.329% | 1.823% / 3.409% | 75.160% / 0.000% |
| cic | history | [42] | 91.379% / 0.326% | 2.084% / 3.454% | 75.571% / 0.000% |
| ctu | core | [42] | 95.518% / 5.797% | 5.653% / 3.490% | 96.153% / 0.949% |
| ctu | derived | [42] | 95.518% / 1.424% | 5.653% / 6.274% | 96.182% / 0.903% |
| ctu | history | [42] | 95.898% / 1.461% | 5.653% / 6.619% | 96.409% / 0.918% |
| mixed | core | [42] | 92.442% / 0.827% | 98.151% / 0.227% | 89.099% / 0.015% |
| mixed | derived | [42] | 92.366% / 0.559% | 97.265% / 0.093% | 88.659% / 0.015% |
| mixed | history | [42] | 92.366% / 0.562% | 98.815% / 0.223% | 88.943% / 0.015% |
| uwf | core | [42] | 99.734% / 43.533% | 100.000% / 0.962% | 94.180% / 44.617% |
| uwf | derived | [42] | 99.962% / 87.526% | 100.000% / 0.946% | 94.450% / 64.483% |
| uwf | history | [42] | 99.772% / 43.153% | 100.000% / 0.929% | 93.371% / 16.863% |

## capture_days: logistic_regression

Each cell is attack recall / benign false-positive rate. Means across listed estimator seeds; no confidence interval is claimed.

| Training source | Inputs | Seeds | CIC | UWF | CTU |
|---|---|---|---:|---:|---:|
| cic | core | [42] | 89.746% / 0.856% | 3.725% / 3.462% | 35.798% / 0.031% |
| cic | derived | [42] | 91.607% / 0.476% | 5.112% / 3.482% | 32.264% / 0.015% |
| cic | history | [42] | 91.607% / 0.474% | 5.653% / 3.490% | 32.292% / 0.015% |
| ctu | core | [42] | 89.404% / 1.022% | 1.394% / 0.008% | 16.863% / 0.031% |
| ctu | derived | [42] | 90.277% / 30.658% | 1.485% / 0.142% | 29.539% / 0.023% |
| ctu | history | [42] | 89.859% / 30.289% | 1.485% / 0.146% | 16.920% / 0.069% |
| mixed | core | [42] | 89.442% / 1.469% | 1.830% / 0.008% | 16.792% / 0.046% |
| mixed | derived | [42] | 87.695% / 1.194% | 46.041% / 0.004% | 0.213% / 1.235% |
| mixed | history | [42] | 87.505% / 1.044% | 45.513% / 0.000% | 7.622% / 1.250% |
| uwf | core | [42] | 67.034% / 21.000% | 100.000% / 1.015% | 96.565% / 45.782% |
| uwf | derived | [42] | 66.692% / 18.886% | 100.000% / 0.990% | 96.153% / 31.743% |
| uwf | history | [42] | 67.148% / 19.705% | 100.000% / 0.998% | 95.841% / 32.168% |

## devices: random_forest

Each cell is attack recall / benign false-positive rate. Means across listed estimator seeds; no confidence interval is claimed.

| Training source | Inputs | Seeds | CIC | UWF | CTU |
|---|---|---|---:|---:|---:|
| cic | core | [42] | 91.265% / 0.326% | 1.410% / 0.196% | 68.619% / 0.520% |
| cic | history | [42] | 91.379% / 0.326% | 2.336% / 4.362% | 74.817% / 0.860% |
| ctu | core | [42] | 0.114% / 56.826% | 0.000% / 90.835% | 0.374% / 64.639% |
| ctu | history | [42] | 0.190% / 56.997% | 0.000% / 90.875% | 0.813% / 65.322% |
| mixed | core | [42] | 92.214% / 0.570% | 97.544% / 0.151% | 3.481% / 0.957% |
| mixed | history | [42] | 89.176% / 0.318% | 96.269% / 0.065% | 4.262% / 0.892% |
| uwf | core | [42] | 0.608% / 16.391% | 97.584% / 0.115% | 0.179% / 4.750% |
| uwf | history | [42] | 2.773% / 17.438% | 94.645% / 0.015% | 1.139% / 8.133% |

## devices: logistic_regression

Each cell is attack recall / benign false-positive rate. Means across listed estimator seeds; no confidence interval is claimed.

| Training source | Inputs | Seeds | CIC | UWF | CTU |
|---|---|---|---:|---:|---:|
| cic | core | [42] | 89.746% / 0.856% | 4.728% / 4.362% | 28.209% / 1.025% |
| cic | history | [42] | 91.607% / 0.474% | 6.302% / 4.432% | 28.843% / 0.538% |
| ctu | core | [42] | 0.114% / 53.028% | 0.000% / 37.924% | 0.000% / 54.397% |
| ctu | history | [42] | 0.114% / 51.915% | 0.000% / 36.689% | 0.016% / 55.727% |
| mixed | core | [42] | 0.152% / 1.223% | 2.013% / 0.010% | 0.065% / 2.032% |
| mixed | history | [42] | 0.038% / 0.016% | 0.000% / 0.000% | 0.033% / 5.775% |
| uwf | core | [42] | 4.406% / 19.919% | 96.129% / 0.035% | 55.214% / 14.076% |
| uwf | history | [42] | 80.972% / 14.813% | 96.154% / 0.035% | 61.363% / 13.116% |

## Scope and limits

Native-domain success is not proof of transfer to another network. UWF seasonal separation, scripted repetition, CTU's selected device population, weak/annotation-dependent labels and shared campaigns remain confounders. ATT&CK labels do not establish observability of host-only behavior in connection records.
The original CIC holdout was examined in previous work. It is a fixed regression/transfer benchmark here, not a fresh final acceptance set. Three estimator seeds do not replace independent captures, hosts, campaigns or future-time evaluation.
No new VM capture, benign alarm-rate measurement, controlled VM attack evaluation, or laptop measurement is claimed. No SSH/VM/network/firewall/service configuration or application database was altered. No candidate is automatically deployed.
Parallel forest aggregation changed an otherwise identical control threshold from 0.9001884181650492 to 0.9001884181650491. With identical trees/scalers this changed 119 decisions in the fixed CIC test set. Final results use one inference worker and recalibrate on validation only. Original parallel runs remain in the ignored results directory; final runs are in results_serial. Runtime inference now also fixes one worker, without changing artifact weights, fingerprint or feature schema.
Derived features and directional history were evaluated offline. Behavioral windows and DNS/HTTP/TLS ingestion were not added: those require a separately validated causal context/telemetry contract, beyond a feature-name mapping.
## Implementation verification

The complete backend unit suite passed: 229 cases, including eight synthetic feature/partition checks added for this study. Four pre-existing Pydantic deprecation warnings remain. These unit checks do not load a real environment file, dataset, deployed artifact, database or VM.
A separate offline runtime smoke check used 500 real Friday CIC source records (not a new statistical holdout). Schema normalization, typed preparation and the live detector agreed with direct model predictions; six repeated inference calls were identical. No SQL, VM or environment file was accessed by this check. The selected artifact SHA-256 remains 5234d410a219d5bfe8f5943116db48e81f38513151ebc5496d96a564e6fdf38b.
## Reproduction

Run from the repository root, with the recorded Python environment:

```powershell
& api/.venv/Scripts/python.exe -B -m ai.study_acquire --source uwf
& api/.venv/Scripts/python.exe -B -m ai.study_acquire --source ctu
& api/.venv/Scripts/python.exe -B -m ai.study_prepare --datasets cic uwf ctu
& api/.venv/Scripts/python.exe -B -m ai.study_experiment --datasets cic uwf ctu --seeds 42 43 44 --mixed
& api/.venv/Scripts/python.exe -B -m ai.study_experiment --datasets cic uwf ctu --seeds 42 --mixed --protocol capture_days
& api/.venv/Scripts/python.exe -B -m ai.study_experiment --datasets cic uwf ctu --seeds 42 --features core history --mixed --protocol devices
& api/.venv/Scripts/python.exe -B -m ai.study_experiment --datasets cic uwf ctu --seeds 42 --features core --mixed --partition-seed 43
& api/.venv/Scripts/python.exe -B -m ai.study_experiment --datasets cic uwf ctu --seeds 42 --features core --mixed --partition-seed 44
& api/.venv/Scripts/python.exe -B -m ai.study_report
```

Raw downloads, prepared tables and candidate artifacts remain Git-ignored under `.ai-workspace/extension/`. Nothing is staged or committed by these commands.
