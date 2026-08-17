"""Tests for the Isolation Forest anomaly detector."""

import numpy as np
from sklearn.ensemble import IsolationForest

from ml.anomaly_detector import AnomalyDetector
from ml.feature_extractor import extract_features


def test_detector_not_ready_without_model(tmp_path, monkeypatch):
    monkeypatch.setenv("ANOMALY_MODEL_PATH", str(tmp_path / "nonexistent.pkl"))
    detector = AnomalyDetector()
    assert detector.is_ready() is False
    assert detector.score([0.1, 0.1, 0.1, 0.1, 0.1, 0.1]) == 0.0
    assert detector.is_anomaly([0.9, 0.9, 0.9, 0.9, 0.9, 0.9]) is False


def test_detector_flags_outlier_after_training(tmp_path, monkeypatch):
    import joblib

    model_path = tmp_path / "isolation_forest.pkl"
    monkeypatch.setenv("ANOMALY_MODEL_PATH", str(model_path))

    # Train on 100 "normal" samples clustered around low values
    rng = np.random.default_rng(42)
    normal_samples = rng.normal(loc=0.2, scale=0.05, size=(100, 6))
    normal_samples = np.clip(normal_samples, 0.0, 1.0)

    model = IsolationForest(contamination=0.1, random_state=42)
    model.fit(normal_samples)
    joblib.dump(model, model_path)

    detector = AnomalyDetector()
    assert detector.is_ready() is True

    # A far-outlier feature vector should score as anomalous
    outlier = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
    assert detector.is_anomaly(outlier) is True

    # A typical "normal" vector should not be anomalous
    normal = [0.2, 0.2, 0.2, 0.2, 0.2, 0.2]
    assert detector.is_anomaly(normal) is False


def test_feature_extractor_six_values_bounded():
    class FakeReq:
        response_time_ms = 500.0
        response_body = '{"a": 1, "b": {"c": 2}}'
        response_status = 404
        response_headers = {"content-type": "application/json"}

    features = extract_features(FakeReq())
    assert len(features) == 6
    assert all(isinstance(f, float) for f in features)
    assert all(0.0 <= f <= 1.0 for f in features)
