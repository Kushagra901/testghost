"""Capture endpoint — receives scrubbed payloads from the mitmproxy addon."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import CapturedRequest, Session, SessionStatus
from backend.db.session import get_db
from backend.schemas.capture import CapturePayload, CaptureResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/capture", response_model=CaptureResponse, status_code=201)
async def capture(
    payload: CapturePayload, db: AsyncSession = Depends(get_db)
) -> CaptureResponse:
    """
    Receive a scrubbed HTTP request+response pair from the mitmproxy addon.
    Runs deduplication and anomaly scoring before persisting.
    """
    # ── Validate session ─────────────────────────────────────
    result = await db.execute(select(Session).where(Session.id == payload.session_id))
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == SessionStatus.COMPLETE:
        raise HTTPException(status_code=409, detail="Session is already stopped")

    # ── Deduplication (imported lazily to avoid circular import) ──
    from ml.deduplicator import Deduplicator
    from ml.embedder import RequestEmbedder
    from ml.store_embedding import store_embedding

    embedder = RequestEmbedder()
    deduplicator = Deduplicator()

    embedding_vector = embedder.embed(
        payload.method, payload.path, payload.request_body or ""
    )
    is_dup, dup_of_id = await deduplicator.is_duplicate(
        payload.session_id, embedding_vector, db
    )

    # ── Anomaly detection ────────────────────────────────────
    from ml.anomaly_detector import AnomalyDetector
    from ml.feature_extractor import extract_features

    detector = AnomalyDetector()
    temp_request = CapturedRequest(
        response_status=payload.response_status,
        response_body=payload.response_body,
        response_headers=payload.response_headers,
        response_time_ms=payload.response_time_ms,
    )
    features = extract_features(temp_request)
    anomaly_score = detector.score(features) if detector.is_ready() else None
    is_anomaly = detector.is_anomaly(features) if detector.is_ready() else False

    # ── Persist ──────────────────────────────────────────────
    captured = CapturedRequest(
        session_id=payload.session_id,
        method=payload.method,
        path=payload.path,
        url=payload.url,
        request_headers=payload.request_headers,
        request_body=payload.request_body,
        response_status=payload.response_status,
        response_body=payload.response_body,
        response_headers=payload.response_headers,
        response_time_ms=payload.response_time_ms,
        is_duplicate=is_dup,
        duplicate_of_id=dup_of_id,
        anomaly_score=anomaly_score,
        is_anomaly=is_anomaly,
    )
    db.add(captured)
    await db.flush()

    if not is_dup:
        await store_embedding(captured.id, embedding_vector, db)

    logger.info(
        "Captured %s %s | dup=%s anomaly=%s",
        payload.method, payload.path, is_dup, is_anomaly,
    )

    return CaptureResponse(
        stored=True,
        request_id=captured.id,
        is_duplicate=is_dup,
        duplicate_of_id=dup_of_id,
    )
