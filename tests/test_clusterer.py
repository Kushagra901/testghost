"""Tests for KMeans endpoint clustering — using synthetic embeddings, no DB needed."""

import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score

from ml.clusterer import _label_from_paths


def test_label_from_paths_detects_auth():
    paths = ["/api/auth/login", "/api/auth/logout", "/api/auth/refresh"]
    assert _label_from_paths(paths) == "auth"


def test_label_from_paths_detects_admin():
    paths = ["/api/admin/dashboard", "/api/admin/users"]
    assert _label_from_paths(paths) == "admin"


def test_label_from_paths_falls_back_to_common_segment():
    paths = ["/api/widgets/1", "/api/widgets/2", "/api/widgets/3"]
    label = _label_from_paths(paths)
    assert label in ("widgets", "general")


def test_kmeans_silhouette_selection_synthetic():
    """Sanity check that silhouette-based k selection picks a reasonable k
    for clearly separated synthetic clusters."""
    rng = np.random.default_rng(0)
    cluster_a = rng.normal(loc=[0, 0], scale=0.05, size=(10, 2))
    cluster_b = rng.normal(loc=[5, 5], scale=0.05, size=(10, 2))
    cluster_c = rng.normal(loc=[-5, 5], scale=0.05, size=(10, 2))
    data = np.vstack([cluster_a, cluster_b, cluster_c])

    best_k, best_score = 2, -1.0
    for k in range(2, 6):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(data)
        score = silhouette_score(data, labels)
        if score > best_score:
            best_k, best_score = k, score

    assert best_k == 3, f"Expected 3 clear clusters, got k={best_k}"
