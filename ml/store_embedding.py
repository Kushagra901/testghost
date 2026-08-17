"""Stores a computed embedding vector into the embeddings table."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Embedding


async def store_embedding(
    captured_request_id: uuid.UUID,
    embedding_vector: list[float],
    db: AsyncSession,
) -> None:
    """Insert a new embedding row. Called only for non-duplicate requests."""
    embedding = Embedding(
        captured_request_id=captured_request_id,
        vector=embedding_vector,
    )
    db.add(embedding)
    await db.flush()
