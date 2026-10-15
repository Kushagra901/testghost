"""
TestGhost v2 — FastAPI application entry point.
"""

import logging
import threading
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.db.init_db import init_db
from backend.routers import capture, generate, sessions

logger = logging.getLogger(__name__)

_embedder_ready = False


def _warm_embedder() -> None:
    global _embedder_ready
    try:
        from ml.embedder import RequestEmbedder
        embedder = RequestEmbedder()
        embedder.embed("GET", "/health", "")
        _embedder_ready = True
        logger.info("Embedding model warmed and ready.")
    except Exception as exc:
        logger.error("Failed to warm embedding model: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup tasks before serving requests."""
    await init_db()
    threading.Thread(target=_warm_embedder, daemon=True).start()
    yield


app = FastAPI(
    title="TestGhost",
    description="AI-native HTTP traffic capture and test generation engine",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sessions.router, prefix="/session", tags=["sessions"])
app.include_router(capture.router, prefix="", tags=["capture"])
app.include_router(generate.router, prefix="", tags=["generate"])


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": "0.2.0"}


@app.get("/ready", tags=["meta"])
async def ready() -> dict[str, str]:
    """Ready check endpoint: returns 200 once embedder is loaded, 503 otherwise."""
    if _embedder_ready:
        return {"status": "ready"}
    raise HTTPException(status_code=503, detail="Embedding model is still loading")
