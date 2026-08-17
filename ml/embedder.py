"""
Sentence-transformer embedding for TestGhost.
Converts captured HTTP requests into 384-dim vectors for pgvector storage.
"""

import json
import logging
import os
import re

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

_PATH_PARAM_PATTERN = re.compile(r"/\d+")
_UUID_PATTERN = re.compile(
    r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE
)


class RequestEmbedder:
    """Loads MiniLM and embeds requests as 384-dim float vectors."""

    MODEL_NAME = "all-MiniLM-L6-v2"

    def __init__(self) -> None:
        cache_dir = os.environ.get("SENTENCE_TRANSFORMERS_HOME", "models/embeddings_cache")
        self._model = SentenceTransformer(self.MODEL_NAME, cache_folder=cache_dir)
        logger.info("Loaded embedding model: %s", self.MODEL_NAME)

    def normalize_path(self, path: str) -> str:
        """Replace numeric IDs and UUIDs with generic placeholders."""
        path = _UUID_PATTERN.sub("/{uuid}", path)
        path = _PATH_PARAM_PATTERN.sub("/{id}", path)
        return path

    def extract_body_schema(self, body: str | None) -> str:
        """Extract top-level JSON keys from request body for embedding."""
        if not body:
            return "no_body"
        try:
            parsed = json.loads(body)
            if isinstance(parsed, dict):
                return "fields:" + ",".join(sorted(parsed.keys()))
            return "array_body"
        except (json.JSONDecodeError, ValueError):
            return "text_body"

    def build_embedding_string(self, method: str, path: str, request_body: str | None) -> str:
        """
        Build the canonical string we embed.
        Format: "METHOD /normalized/path fields:key1,key2"
        """
        normalized_path = self.normalize_path(path)
        body_schema = self.extract_body_schema(request_body)
        return f"{method.upper()} {normalized_path} {body_schema}"

    def embed(self, method: str, path: str, request_body: str | None) -> list[float]:
        """Return a 384-dim embedding vector as a Python list of floats."""
        text = self.build_embedding_string(method, path, request_body)
        vector = self._model.encode(text, normalize_embeddings=True)
        return vector.tolist()
