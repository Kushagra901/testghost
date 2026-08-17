"""Pydantic schemas for session endpoints."""

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class StartSessionRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255, example="checkout-flow-test")


class StartSessionResponse(BaseModel):
    session_id: uuid.UUID
    name: str
    status: str


class StopSessionRequest(BaseModel):
    session_id: uuid.UUID


class StopSessionResponse(BaseModel):
    session_id: uuid.UUID
    status: str
    request_count: int
    duration_seconds: float | None


class SessionListItem(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    request_count: int
    unique_endpoints: int
    anomaly_count: int
    created_at: datetime
    ended_at: datetime | None

    model_config = {"from_attributes": True}
