"""Pydantic schemas for the capture endpoint."""

import uuid

from pydantic import BaseModel, Field


class CapturePayload(BaseModel):
    session_id: uuid.UUID
    method: str = Field(..., max_length=10, example="POST")
    path: str = Field(..., example="/api/users")
    url: str = Field(..., example="https://myapp.com/api/users")
    request_headers: dict = Field(default_factory=dict)
    request_body: str | None = None
    response_status: int = Field(..., ge=100, le=599, example=200)
    response_body: str | None = None
    response_headers: dict = Field(default_factory=dict)
    response_time_ms: float | None = Field(None, ge=0)


class CaptureResponse(BaseModel):
    stored: bool
    request_id: uuid.UUID | None
    is_duplicate: bool
    duplicate_of_id: uuid.UUID | None


class GenerateRequest(BaseModel):
    session_id: uuid.UUID


class GenerateResponse(BaseModel):
    session_id: uuid.UUID
    report_path: str
    test_files: list[str]
    summary: dict
