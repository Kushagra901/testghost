"""Session management endpoints."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import CapturedRequest, Session, SessionStatus
from backend.db.session import get_db
from backend.schemas.session import (
    SessionListItem,
    StartSessionRequest,
    StartSessionResponse,
    StopSessionRequest,
    StopSessionResponse,
)

router = APIRouter()


@router.post("/start", response_model=StartSessionResponse, status_code=201)
async def start_session(
    body: StartSessionRequest, db: AsyncSession = Depends(get_db)
) -> StartSessionResponse:
    """Create a new recording session. Returns the session_id to pass to the proxy."""
    session = Session(name=body.name, status=SessionStatus.ACTIVE)
    db.add(session)
    await db.flush()
    return StartSessionResponse(
        session_id=session.id, name=session.name, status=session.status.value
    )


@router.post("/stop", response_model=StopSessionResponse)
async def stop_session(
    body: StopSessionRequest, db: AsyncSession = Depends(get_db)
) -> StopSessionResponse:
    """Mark a session as complete and return capture statistics."""
    result = await db.execute(select(Session).where(Session.id == body.session_id))
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == SessionStatus.COMPLETE:
        raise HTTPException(status_code=409, detail="Session is already stopped")

    session.status = SessionStatus.COMPLETE
    session.ended_at = datetime.now(timezone.utc)

    count_result = await db.execute(
        select(func.count()).where(CapturedRequest.session_id == body.session_id)
    )
    request_count = count_result.scalar_one()

    duration = None
    if session.created_at and session.ended_at:
        duration = (session.ended_at - session.created_at).total_seconds()

    return StopSessionResponse(
        session_id=session.id,
        status=SessionStatus.COMPLETE.value,
        request_count=request_count,
        duration_seconds=duration,
    )


@router.get("/list", response_model=list[SessionListItem])
async def list_sessions(db: AsyncSession = Depends(get_db)) -> list[SessionListItem]:
    """List all past sessions with summary statistics."""
    result = await db.execute(select(Session).order_by(Session.created_at.desc()))
    sessions = result.scalars().all()

    items = []
    for s in sessions:
        req_count = await db.execute(
            select(func.count()).where(CapturedRequest.session_id == s.id)
        )
        unique_q = await db.execute(
            select(func.count())
            .where(CapturedRequest.session_id == s.id)
            .where(CapturedRequest.is_duplicate == False)  # noqa: E712
        )
        anomaly_q = await db.execute(
            select(func.count())
            .where(CapturedRequest.session_id == s.id)
            .where(CapturedRequest.is_anomaly == True)  # noqa: E712
        )
        items.append(
            SessionListItem(
                id=s.id,
                name=s.name,
                status=s.status.value,
                request_count=req_count.scalar_one(),
                unique_endpoints=unique_q.scalar_one(),
                anomaly_count=anomaly_q.scalar_one(),
                created_at=s.created_at,
                ended_at=s.ended_at,
            )
        )
    return items
