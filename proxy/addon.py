import json
import logging
import os
import queue
import threading
import time
from typing import Any

import httpx
from mitmproxy import http

from proxy.scrubber import PIIScrubber

logger = logging.getLogger(__name__)

# Paths to always skip — noise reduction
SKIP_PATHS = {
    "/favicon.ico", "/robots.txt", "/.well-known",
    "/health", "/ready", "/metrics", "/static",
}

SKIP_EXTENSIONS = {".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".woff", ".woff2"}


class TestGhostAddon:
    """mitmproxy addon that captures request/response pairs for TestGhost."""

    def __init__(self) -> None:
        self.session_id: str = os.environ.get("SESSION_ID", "")
        self.backend_url: str = os.environ.get("BACKEND_URL", "http://localhost:8000")
        self.scrubber = PIIScrubber()
        self._pending: dict[str, float] = {}  # flow_id -> start_time
        self._client = httpx.Client(timeout=30.0)
        self._queue: queue.Queue[dict[str, Any] | None] = queue.Queue()
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

        if not self.session_id:
            logger.warning("SESSION_ID not set — captures will be rejected by the backend.")

    def _should_skip(self, flow: http.HTTPFlow) -> bool:
        path = flow.request.path
        if any(path.startswith(skip) for skip in SKIP_PATHS):
            return True
        if any(path.endswith(ext) for ext in SKIP_EXTENSIONS):
            return True
        # Skip testghost's own backend calls
        if self.backend_url in flow.request.pretty_url:
            return True
        return False

    def request(self, flow: http.HTTPFlow) -> None:
        """Record request start time."""
        if not self._should_skip(flow):
            self._pending[flow.id] = time.monotonic()

    def response(self, flow: http.HTTPFlow) -> None:
        """Capture complete request+response and queue asynchronously."""
        if self._should_skip(flow) or flow.id not in self._pending:
            return

        start_time = self._pending.pop(flow.id)
        response_time_ms = (time.monotonic() - start_time) * 1000

        try:
            # PII scrubbing happens here before the payload is queued
            payload = self._build_payload(flow, response_time_ms)
            self._queue.put(payload)
        except Exception as exc:
            logger.warning("TestGhost capture failed for %s: %s", flow.request.path, exc)

    def _build_payload(self, flow: http.HTTPFlow, response_time_ms: float) -> dict[str, Any]:
        req = flow.request
        resp = flow.response

        raw_req_body = req.get_text(strict=False) if req.content else None
        raw_resp_body = resp.get_text(strict=False) if resp and resp.content else None

        req_body = self.scrubber.truncate_body(self.scrubber.scrub_body(raw_req_body))
        resp_body = self.scrubber.truncate_body(self.scrubber.scrub_body(raw_resp_body))

        req_headers = dict(req.headers)
        resp_headers = dict(resp.headers) if resp else {}

        # Scrub sensitive header values
        for sensitive in ("authorization", "cookie", "set-cookie", "x-api-key"):
            if sensitive in req_headers:
                req_headers[sensitive] = "[SCRUBBED_HEADER]"

        return {
            "session_id": self.session_id,
            "method": req.method,
            "path": req.path,
            "url": req.pretty_url,
            "request_headers": req_headers,
            "request_body": req_body,
            "response_status": resp.status_code if resp else 0,
            "response_body": resp_body,
            "response_headers": resp_headers,
            "response_time_ms": round(response_time_ms, 2),
        }

    def _worker(self) -> None:
        while True:
            payload = self._queue.get()
            if payload is None:
                break
            try:
                self._send_with_retry(payload)
            except Exception as exc:
                logger.error("Unexpected error sending capture: %s", exc)
            finally:
                self._queue.task_done()

    def _send_with_retry(self, payload: dict[str, Any]) -> None:
        path = payload.get("path", "")
        for attempt in range(2):
            try:
                response = self._client.post(
                    f"{self.backend_url}/capture",
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                if response.status_code in (200, 201):
                    return
                logger.warning(
                    "Backend returned %s for capture %s (attempt %d/2)",
                    response.status_code, path, attempt + 1
                )
            except httpx.RequestError as exc:
                logger.warning(
                    "Could not reach TestGhost backend for %s (attempt %d/2): %s",
                    path, attempt + 1, exc
                )
            if attempt == 0:
                time.sleep(1.0)

        logger.error("Capture permanently dropped for %s after 2 failed attempts.", path)

    def done(self) -> None:
        """Drain queue on shutdown."""
        try:
            self._queue.join()
        except Exception:
            pass


# mitmproxy expects this at module level
addons = [TestGhostAddon()]
