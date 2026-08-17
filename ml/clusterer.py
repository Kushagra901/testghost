"""
KMeans semantic clustering of captured endpoints.
Groups endpoints by embedding similarity and assigns human-readable labels.
"""

import logging
import os
import uuid

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import CapturedRequest, Embedding

logger = logging.getLogger(__name__)

MIN_REQUESTS = int(os.environ.get("MIN_REQUESTS_FOR_CLUSTERING", "6"))

_LABEL_HINTS: list[tuple[list[str], str]] = [
    (["auth", "login", "logout", "token", "signin", "signup", "register", "password"], "auth"),
    (["user", "profile", "account", "me", "member"], "users"),
    (["admin", "manage", "dashboard", "staff", "internal"], "admin"),
    (["product", "item", "catalog", "inventory", "listing"], "products"),
    (["order", "cart", "checkout", "payment", "purchase"], "orders"),
    (["search", "filter", "query", "find"], "search"),
    (["webhook", "event", "callback", "notify"], "webhooks"),
]


def _label_from_paths(paths: list[str]) -> str:
    """Heuristically label a cluster from the paths it contains."""
    combined = " ".join(paths).lower()
    for keywords, label in _LABEL_HINTS:
        if any(kw in combined for kw in keywords):
            return label
    # Fall back to the most common path segment
    segments: list[str] = []
    for p in paths:
        parts = [s for s in p.strip("/").split("/") if s and not s.isdigit()]
        if parts:
            segments.append(parts[0])
    if segments:
        return max(set(segments), key=segments.count)
    return "general"


async def cluster_session(
    session_id: uuid.UUID, db: AsyncSession
) -> dict[int, str]:
    """
    Cluster all non-duplicate captured requests for a session.
    Returns {cluster_id: cluster_label}.
    """
    result = await db.execute(
        select(CapturedRequest, Embedding)
        .join(Embedding, Embedding.captured_request_id == CapturedRequest.id)
        .where(CapturedRequest.session_id == session_id)
        .where(CapturedRequest.is_duplicate == False)  # noqa: E712
    )
    rows = result.all()

    if not rows:
        logger.warning("No non-duplicate requests with embeddings for session %s", session_id)
        return {0: "general"}

    if len(rows) < MIN_REQUESTS:
        logger.info("Too few requests (%d) — assigning single cluster 'general'", len(rows))
        for req, _ in rows:
            req.cluster_id = 0
            req.cluster_label = "general"
        return {0: "general"}

    request_ids = [row[0].id for row in rows]
    vectors = np.array([row[1].vector for row in rows], dtype=float)
    paths = [row[0].path for row in rows]

    # Select k by silhouette score
    best_k, best_score = 2, -1.0
    max_k = min(8, len(rows) // 2)
    for k in range(2, max_k + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(vectors)
        score = silhouette_score(vectors, labels)
        logger.debug("k=%d silhouette=%.4f", k, score)
        if score > best_score:
            best_score = score
            best_k = k

    logger.info("Chosen k=%d (silhouette=%.4f) for session %s", best_k, best_score, session_id)

    km_final = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    cluster_assignments = km_final.fit_predict(vectors)

    # Build label map
    cluster_paths: dict[int, list[str]] = {i: [] for i in range(best_k)}
    for idx, cluster_id in enumerate(cluster_assignments):
        cluster_paths[int(cluster_id)].append(paths[idx])

    cluster_labels: dict[int, str] = {
        cid: _label_from_paths(cpaths) for cid, cpaths in cluster_paths.items()
    }

    # Persist assignments
    for idx, (req, _) in enumerate(rows):
        cid = int(cluster_assignments[idx])
        req.cluster_id = cid
        req.cluster_label = cluster_labels[cid]

    return cluster_labels
