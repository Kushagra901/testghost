"""Tests for the request embedder and deduplication logic."""

from ml.embedder import RequestEmbedder


def test_embed_returns_384_dims():
    embedder = RequestEmbedder()
    vec = embedder.embed("GET", "/api/users/123", None)
    assert len(vec) == 384


def test_path_normalization():
    embedder = RequestEmbedder()
    assert embedder.normalize_path("/api/users/123") == "/api/users/{id}"
    assert "uuid" in embedder.normalize_path("/api/items/550e8400-e29b-41d4-a716-446655440000")


def test_similar_paths_produce_similar_vectors():
    embedder = RequestEmbedder()
    v1 = embedder.embed("GET", "/api/users/1", None)
    v2 = embedder.embed("GET", "/api/users/2", None)
    # Dot product of normalized vectors ≈ cosine similarity
    similarity = sum(a * b for a, b in zip(v1, v2))
    assert similarity > 0.95, f"Same endpoint pattern should be very similar: {similarity}"


def test_different_endpoints_produce_different_vectors():
    embedder = RequestEmbedder()
    v1 = embedder.embed("POST", "/api/auth/login", '{"email":"x","password":"y"}')
    v2 = embedder.embed("GET", "/api/products/1", None)
    similarity = sum(a * b for a, b in zip(v1, v2))
    assert similarity < 0.90, f"Different endpoints should not be near-identical: {similarity}"
