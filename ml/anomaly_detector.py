"""
Isolation Forest anomaly detector for TestGhost.
Flags HTTP responses that are statistically unusual.
"""

import logging
import os
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

logger = logging.getLogger(__name__)

MODEL_PATH = Path(os.environ.get("ANOMALY_MODEL_PATH", "models/isolation_forest.pkl"))
THRESHOLD = float(os.environ.get("ANOMALY_SCORE_THRESHOLD", "-0.1"))


class AnomalyDetector:
    """Loads a pre-trained IsolationForest and scores response features."""

    def __init__(self) -> None:
        self._model: IsolationForest | None = None
        self._load()

    def _load(self) -> None:
        if MODEL_PATH.exists():
            try:
                self._model = joblib.load(MODEL_PATH)
                logger.info("Loaded anomaly model from %s", MODEL_PATH)
            except Exception as exc:
                logger.warning("Could not load anomaly model: %s", exc)
                self._model = None
        else:
            logger.info("No anomaly model found at %s — scoring disabled until training.", MODEL_PATH)

    def is_ready(self) -> bool:
        return self._model is not None

    def score(self, features: list[float]) -> float:
        """Return the anomaly decision function score. Lower = more anomalous."""
        if self._model is None:
            return 0.0
        arr = np.array(features, dtype=float).reshape(1, -1)
        return float(self._model.decision_function(arr)[0])

    def is_anomaly(self, features: list[float]) -> bool:
        """Return True if the response is anomalous (score below threshold)."""
        return self.score(features) < THRESHOLD
