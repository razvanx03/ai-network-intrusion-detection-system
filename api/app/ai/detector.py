"""Load a locally selected classifier and emit review findings, not confirmed attacks."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn

from app.ai.features import FEATURE_COLUMNS, FEATURE_VERSION, feature_frame

DIRECTORY = Path(__file__).resolve().parent
DEPLOYMENT_PATH = DIRECTORY / "deployment.json"


class ConnectionClassifier:
    configured = True

    def __init__(self, manifest: dict):
        path = (DIRECTORY / manifest["artifact"]).resolve()
        if not path.is_relative_to((DIRECTORY / "models").resolve()):
            raise ValueError("AI artifact must be inside the local models directory")
        if not path.is_file():
            raise FileNotFoundError(f"Selected AI artifact is missing: {path}. Reproduce or transfer the selected model.")
        checksum = hashlib.sha256(path.read_bytes()).hexdigest()
        if checksum != manifest["sha256"]:
            raise ValueError("Selected AI artifact checksum does not match deployment.json")
        # joblib is executable serialization. Only locally trained, verified artifacts belong here.
        bundle = joblib.load(path)
        expected_versions = {"sklearn": sklearn.__version__, "numpy": np.__version__,
                             "pandas": pd.__version__, "joblib": joblib.__version__}
        if bundle["versions"] != expected_versions:
            raise ValueError(f"AI dependency versions differ: expected {bundle['versions']}, installed {expected_versions}")
        if bundle["feature_version"] != FEATURE_VERSION or tuple(bundle["feature_columns"]) != FEATURE_COLUMNS:
            raise ValueError("Selected model has an incompatible connection feature schema")
        if bundle["kind"] not in {"random_forest", "logistic_regression"}:
            raise ValueError("Only evaluated supervised classifiers can be deployed by this adapter")
        threshold = float(bundle["threshold"])
        if not np.isfinite(threshold) or threshold < 0 or threshold > 1:
            raise ValueError("Classifier threshold must be finite and within [0, 1]")
        self.model = bundle["model"]
        if bundle["kind"] == "random_forest":
            # Parallel floating-point summation can change a tied probability
            # by one ULP and flip the comparison at the calibrated threshold.
            self.model.set_params(model__n_jobs=1)
        if not np.array_equal(self.model.classes_, [0, 1]):
            raise ValueError("Selected classifier must use class order [benign=0, attack=1]")
        self.threshold = threshold
        self.name = f"{bundle['kind']}_{bundle['dataset']}"
        self.version = f"{FEATURE_VERSION}:{checksum[:12]}"

    def analyze_batch(self, connections):
        from app.ai.engine import Finding

        if not connections:
            return []
        rows = [connection.record.model_dump() for connection in connections]
        scores = self.model.predict_proba(feature_frame(rows))[:, 1]
        if len(scores) != len(connections) or not np.isfinite(scores).all() or ((scores < 0) | (scores > 1)).any():
            raise ValueError("Classifier returned invalid connection scores")
        return [Finding(
            connection_ids=[connection.connection_id],
            timestamp=datetime.fromtimestamp(connection.record.ts, tz=timezone.utc),
            attack_type="Suspicious Connection", severity="MEDIUM", confidence=float(score),
            description="connection_model_review", mitre_technique=None,
        ) for connection, score in zip(connections, scores, strict=True) if score >= self.threshold]


def load_detector():
    if not DEPLOYMENT_PATH.is_file():
        raise FileNotFoundError(f"AI deployment configuration is missing: {DEPLOYMENT_PATH}")
    manifest = json.loads(DEPLOYMENT_PATH.read_text(encoding="utf-8"))
    if manifest.get("enabled") is False:
        from app.ai.engine import UnconfiguredDetector
        return UnconfiguredDetector()
    if manifest.get("enabled") is not True:
        raise ValueError("AI deployment must explicitly set enabled to true or false")
    return ConnectionClassifier(manifest)
