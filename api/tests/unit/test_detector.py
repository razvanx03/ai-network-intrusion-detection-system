import hashlib
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import joblib
import numpy as np
import pandas as pd
import pytest
import sklearn

from app.ai import detector as module
from app.ai.engine import UnconfiguredDetector
from app.ai.features import FEATURE_COLUMNS, FEATURE_VERSION
from app.ai.preparation import prepare_connections


@pytest.fixture
def artifact(tmp_path, monkeypatch):
    models = tmp_path / "models"
    models.mkdir()
    path = models / "unit.joblib"
    # Not a serialized model: deserialization is mocked, checksum validation is real.
    path.write_bytes(b"unit-artifact-placeholder")
    manifest = {"enabled": True, "artifact": "models/unit.joblib",
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
    model = SimpleNamespace(classes_=np.array([0, 1]), predict_proba=MagicMock())
    bundle = {
        "versions": {"sklearn": sklearn.__version__, "numpy": np.__version__,
                     "pandas": pd.__version__, "joblib": joblib.__version__},
        "feature_version": FEATURE_VERSION, "feature_columns": list(FEATURE_COLUMNS),
        "kind": "random_forest", "dataset": "unit", "threshold": 0.5, "model": model,
    }
    loader = MagicMock(return_value=bundle)
    monkeypatch.setattr(module, "DIRECTORY", tmp_path)
    monkeypatch.setattr(module, "DEPLOYMENT_PATH", tmp_path / "deployment.json")
    monkeypatch.setattr(module.joblib, "load", loader)
    return manifest, bundle, model, loader


def test_threshold_boundary_and_findings_preserve_evidence(artifact, connection_factory):
    manifest, bundle, model, loader = artifact
    model.predict_proba.return_value = np.array([[0.501, 0.499], [0.5, 0.5], [0.1, 0.9]])
    classifier = module.ConnectionClassifier(manifest)
    findings = classifier.analyze_batch(prepare_connections([connection_factory(i) for i in [1, 2, 3]]))
    assert [finding.connection_ids for finding in findings] == [[2], [3]]
    assert [finding.confidence for finding in findings] == [0.5, 0.9]
    assert all(finding.timestamp.timestamp() == 1700000000.5 for finding in findings)
    assert all(finding.mitre_technique is None and finding.severity == "MEDIUM" for finding in findings)
    assert all(finding.attack_type == "Suspicious Connection" for finding in findings)
    assert tuple(model.predict_proba.call_args.args[0].columns) == FEATURE_COLUMNS
    assert classifier.name == "random_forest_unit"
    loader.assert_called_once()


def test_empty_input_does_not_invoke_model(artifact):
    manifest, _, model, _ = artifact
    assert module.ConnectionClassifier(manifest).analyze_batch(()) == []
    model.predict_proba.assert_not_called()


@pytest.mark.parametrize("scores", [[float("nan")], [float("inf")], [-0.1], [1.1], [0.1, 0.2]])
def test_invalid_model_scores_are_rejected(artifact, connection_factory, scores):
    manifest, _, model, _ = artifact
    model.predict_proba.return_value = np.array([[0.0, value] for value in scores])
    classifier = module.ConnectionClassifier(manifest)
    with pytest.raises(ValueError, match="invalid connection scores"):
        classifier.analyze_batch(prepare_connections([connection_factory()]))


@pytest.mark.parametrize("artifact_name", ["../outside.joblib", "unit.joblib", "models/../../outside.joblib"])
def test_artifact_must_stay_in_models_directory(artifact, artifact_name):
    manifest, _, _, loader = artifact
    with pytest.raises(ValueError, match="inside the local models"):
        module.ConnectionClassifier({**manifest, "artifact": artifact_name})
    loader.assert_not_called()


def test_missing_artifact_fails_before_deserialization(artifact):
    manifest, _, _, loader = artifact
    with pytest.raises(FileNotFoundError):
        module.ConnectionClassifier({**manifest, "artifact": "models/missing.joblib"})
    loader.assert_not_called()


def test_corrupted_artifact_fails_before_deserialization(artifact):
    manifest, _, _, loader = artifact
    with pytest.raises(ValueError, match="checksum"):
        module.ConnectionClassifier({**manifest, "sha256": "0" * 64})
    loader.assert_not_called()


@pytest.mark.parametrize("key,value", [
    ("versions", {}), ("feature_version", "unsupported"), ("feature_columns", []),
    ("kind", "isolation_forest"), ("threshold", -0.01), ("threshold", 1.01),
    ("threshold", float("nan")), ("threshold", float("inf")),
])
def test_incompatible_bundles_fail_fast(artifact, key, value):
    manifest, bundle, _, _ = artifact
    bundle[key] = value
    with pytest.raises(ValueError):
        module.ConnectionClassifier(manifest)


@pytest.mark.parametrize("classes", [[1, 0], [0], [0, 1, 2]])
def test_class_order_cannot_silently_invert_attack_probability(artifact, classes):
    manifest, _, model, _ = artifact
    model.classes_ = np.array(classes)
    with pytest.raises(ValueError, match="class order"):
        module.ConnectionClassifier(manifest)


def test_explicit_disabled_deployment_needs_no_artifact(artifact):
    module.DEPLOYMENT_PATH.write_text(json.dumps({"enabled": False}), encoding="utf-8")
    assert isinstance(module.load_detector(), UnconfiguredDetector)
    artifact[3].assert_not_called()


@pytest.mark.parametrize("manifest", [{}, {"enabled": 0}, {"enabled": 1}, {"enabled": "true"}])
def test_deployment_requires_explicit_boolean(artifact, manifest):
    module.DEPLOYMENT_PATH.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="explicitly"):
        module.load_detector()


def test_missing_deployment_is_not_silently_disabled(artifact):
    with pytest.raises(FileNotFoundError):
        module.load_detector()


def test_enabled_deployment_loads_validated_classifier(artifact):
    module.DEPLOYMENT_PATH.write_text(json.dumps(artifact[0]), encoding="utf-8")
    assert module.load_detector().configured is True
