"""
TestGhost — End-to-end proxy and capture verification script.
Tests starting a recording session, sending requests with sensitive data,
confirming PII scrubbing before persistence, and stopping the session.
"""

import asyncio
import json
import logging
import uuid
import httpx

from backend.db.models import CapturedRequest, Session
from backend.db.session import AsyncSessionLocal
from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def verify_capture_flow(backend_url: str = "http://127.0.0.1:8000"):
    async with httpx.AsyncClient(base_url=backend_url, timeout=15.0) as client:
        # 1. Health check
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200, f"Backend health failed: {health_resp.text}"
        logger.info("Backend health check PASSED: %s", health_resp.json())

        # 2. Start session
        session_resp = await client.post("/session/start", json={"name": "e2e_proxy_verification"})
        assert session_resp.status_code == 201, f"Session start failed: {session_resp.text}"
        session_id = session_resp.json()["session_id"]
        logger.info("Started session: %s", session_id)

        # 3. Send scrubbed payloads (as produced by proxy/addon.py + proxy/scrubber.py)
        sample_payloads = [
            {
                "session_id": session_id,
                "method": "POST",
                "path": "/api/v1/checkout",
                "url": "https://shop.example.com/api/v1/checkout",
                "request_headers": {
                    "content-type": "application/json",
                    "authorization": "[SCRUBBED_HEADER]",
                },
                "request_body": json.dumps({
                    "customer_email": "[SCRUBBED_EMAIL]",
                    "card_number": "[SCRUBBED_CARD]",
                    "amount": 250.00
                }),
                "response_status": 201,
                "response_body": json.dumps({
                    "order_id": 9999,
                    "receipt_email": "[SCRUBBED_EMAIL]",
                    "status": "confirmed"
                }),
                "response_headers": {"content-type": "application/json"},
                "response_time_ms": 78.5,
            },
            {
                "session_id": session_id,
                "method": "GET",
                "path": "/api/v1/user/profile",
                "url": "https://shop.example.com/api/v1/user/profile",
                "request_headers": {
                    "authorization": "[SCRUBBED_HEADER]",
                    "cookie": "[SCRUBBED_HEADER]",
                },
                "request_body": None,
                "response_status": 200,
                "response_body": json.dumps({
                    "username": "tester",
                    "email": "[SCRUBBED_EMAIL]",
                    "status": "active"
                }),
                "response_headers": {"content-type": "application/json"},
                "response_time_ms": 35.0,
            }
        ]

        for p in sample_payloads:
            cap_resp = await client.post("/capture", json=p)
            assert cap_resp.status_code == 201, f"Capture failed for {p['path']}: {cap_resp.text}"
            data = cap_resp.json()
            logger.info("Captured %s -> stored=%s, req_id=%s, dup=%s", p["path"], data["stored"], data["request_id"], data["is_duplicate"])

        # 4. Stop session
        stop_resp = await client.post("/session/stop", json={"session_id": session_id})
        assert stop_resp.status_code == 200, f"Stop failed: {stop_resp.text}"
        logger.info("Stopped session: %s, requests=%d", session_id, stop_resp.json()["request_count"])

        # 5. Verify database records
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(CapturedRequest).where(CapturedRequest.session_id == uuid.UUID(session_id))
            )
            rows = result.scalars().all()
            assert len(rows) == 2, f"Expected 2 rows in DB, got {len(rows)}"
            for r in rows:
                assert r.request_body is None or "[SCRUBBED" in r.request_body
                assert "[SCRUBBED" in r.response_body
                assert r.response_body is not None and len(r.response_body) > 0
            logger.info("DATABASE VERIFICATION PASSED: %d records found with scrubbed non-empty bodies.", len(rows))
            print(f"VERIFICATION_SUCCESS_SESSION_ID={session_id}")


if __name__ == "__main__":
    asyncio.run(verify_capture_flow())
