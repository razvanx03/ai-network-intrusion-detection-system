# Model evaluation boundaries

The selected runtime classifier is a Random Forest trained on the Zeek-derived
CIC-IDS2017 experiment. Selection and artifact identity are explicit in
`api/app/ai/deployment.json`; consult the current manifest rather than treating
this historical selection as permanently fixed.

The versioned `ai/` directory retains acquisition, training, comparison and reporting
code, including experiments not selected for deployment. It is useful for evidence
and reproduction; do not delete it merely because one model is deployed. Downloaded
data and generated experiment outputs belong in the ignored `.ai-workspace/`.

A finding is a suspicious-connection screening result. A classifier score is not a
calibrated attack probability or an identified attack family. Offline results and
controlled VM scenarios do not establish universal detection or the alarm rate on
arbitrary traffic. Ordinary browsing does not automatically improve the model.

Keep training and inference preprocessing aligned. Replacing the artifact requires
an intentional deployment-manifest update; the SHA256 check must not be bypassed.
Joblib artifacts are executable-trust inputs, not harmless datasets.

Evidence: `ai/README.md`, measured reports in `ai/reports/`, the deployment manifest
and runtime AI engine. Backend unit tests must continue using simulated boundaries,
not real datasets, deployed artifacts, VM access, production `.env` or the database.

Selected artifact publication (2026-11-15): user explicitly requested that
api/app/ai/models/selected.joblib be versioned on main for complete fresh clones.
Only that artifact is excepted from *.joblib; datasets and experimental models
remain ignored. The published artifact must match deployment.json SHA-256 and
pinned runtime requirements. Separate model transfer is unnecessary for fresh
clones containing this change.
