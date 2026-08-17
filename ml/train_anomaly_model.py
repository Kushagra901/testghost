"""
Trains the Isolation Forest model on accumulated captured requests.
Run manually: python -m ml.train_anomaly_model
Or via Celery task (future).
"""

import logging
import os
from pathlib import Path

import asyncio
import joblib
import numpy as np
from sklearn.ensemble import IsolationForest
from sqlalchemy import select

from backend.db.models import CapturedRequest
from backend.db.session import AsyncSessionLocal
from ml.feature_extractor import extract_features

logger = logging.getLogger(__name__)

MODEL_PATH = Path(os.environ.get("ANOMALY_MODEL_PATH", "models/isolation_forest.pkl"))
MIN_SAMPLES = int(os.environ.get("MIN_REQUESTS_FOR_ANOMALY_TRAINING", "50"))


async def train_model() -> None:
    """Load all non-anomaly-scored requests, extract features, train + save model."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(CapturedRequest)
            .where(CapturedRequest.anomaly_score == None)  # noqa: E711
            .limit(10_000)
        )
        requests = result.scalars().all()

    if len(requests) < MIN_SAMPLES:
        logger.warning(
            "Not enough samples to train (%d < %d). Skipping.", len(requests), MIN_SAMPLES
        )
        return

    features = [extract_features(r) for r in requests]
    X = np.array(features, dtype=float)

    model = IsolationForest(contamination=0.1, random_state=42, n_estimators=100)
    model.fit(X)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    logger.info("Anomaly model trained on %d samples, saved to %s", len(requests), MODEL_PATH)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(train_model())
