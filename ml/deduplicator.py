"""
RAG-style semantic deduplication using pgvector cosine similarity.
"""

import logging
import os
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

THRESHOLD = float(os.environ.get("DEDUP_SIMILARITY_THRESHOLD", "0.92"))


class Deduplicator:
    """Checks if a semantically identical endpoint was already captured in this session."""

    async def is_duplicate(
        self,
        session_id: uuid.UUID,
        embedding_vector: list[float],
        db: AsyncSession,
    ) -> tuple[bool, uuid.UUID | None]:
        """
        Returns (True, matching_request_id) if a near-identical embedding exists.
        Uses pgvector cosine distance: 1 - (distance) = similarity.
        """
        vector_str = "[" + ",".join(str(f) for f in embedding_vector) + "]"

        query = text("""
            SELECT cr.id, (1 - (e.vector <=> CAST(:vec AS vector))) AS similarity
            FROM embeddings e
            JOIN captured_requests cr ON cr.id = e.captured_request_id
            WHERE cr.session_id = :session_id
            ORDER BY e.vector <=> CAST(:vec AS vector)
            LIMIT 1
        """)

        result = await db.execute(
            query,
            {"vec": vector_str, "session_id": str(session_id)},
        )
        row = result.fetchone()

        if row is None:
            return False, None

        similarity: float = float(row.similarity)
        logger.debug("Top similarity: %.4f (threshold: %.2f)", similarity, THRESHOLD)

        if similarity >= THRESHOLD:
            return True, uuid.UUID(str(row.id))

        return False, None
