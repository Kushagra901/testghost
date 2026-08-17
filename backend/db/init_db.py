"""
Creates all tables on FastAPI startup.
Alembic handles migrations in production — this is for dev convenience.
"""

import logging

from backend.db.models import Base
from backend.db.session import engine

logger = logging.getLogger(__name__)


async def init_db() -> None:
    """Create all tables if they do not exist. Safe to call on every startup."""
    async with engine.begin() as conn:
        # Import models so they are registered on Base.metadata
        from backend.db import models  # noqa: F401

        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables verified/created.")
