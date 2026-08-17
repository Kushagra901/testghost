"""
TestGhost v2 — FastAPI application entry point.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.db.init_db import init_db
from backend.routers import capture, generate, sessions


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Run startup tasks before serving requests."""
    await init_db()
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
