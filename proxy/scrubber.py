"""
PII scrubber for TestGhost.
Strips sensitive data from captured HTTP payloads before they touch the database.
"""

import json
import re
from typing import Any


class PIIScrubber:
    """Recursively scrubs PII from any dict, list, or string value."""

    PATTERNS: list[tuple[str, str]] = [
        # JWT / Bearer tokens (must run first — longest match)
        (r"Bearer\s+[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+", "[SCRUBBED_JWT]"),
        (r"[A-Za-z0-9\-_]{20,}\.[A-Za-z0-9\-_]{20,}\.[A-Za-z0-9\-_]{20,}", "[SCRUBBED_JWT]"),
        # Email addresses
        (r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", "[SCRUBBED_EMAIL]"),
        # Indian Aadhaar (12 digits, often space-separated)
        (r"\b\d{4}\s\d{4}\s\d{4}\b", "[SCRUBBED_AADHAAR]"),
        # Indian PAN
        (r"\b[A-Z]{5}[0-9]{4}[A-Z]\b", "[SCRUBBED_PAN]"),
        # Credit card numbers (Luhn format)
        (r"\b(?:\d[ \-]?){13,16}\b", "[SCRUBBED_CARD]"),
        # US SSN
        (r"\b\d{3}-\d{2}-\d{4}\b", "[SCRUBBED_SSN]"),
        # Phone numbers (international)
        (r"\+?[\d\s\-().]{10,15}", "[SCRUBBED_PHONE]"),
        # IPv4 addresses in request bodies (not URLs)
        (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[SCRUBBED_IP]"),
    ]

    def __init__(self) -> None:
        self._compiled = [
            (re.compile(pattern), replacement)
            for pattern, replacement in self.PATTERNS
        ]

    def scrub_string(self, value: str) -> str:
        """Apply all PII patterns to a string."""
        for regex, replacement in self._compiled:
            value = regex.sub(replacement, value)
        return value

    def scrub(self, data: Any) -> Any:
        """Recursively scrub PII from any structure."""
        if isinstance(data, str):
            return self.scrub_string(data)
        if isinstance(data, dict):
            return {k: self.scrub(v) for k, v in data.items()}
        if isinstance(data, list):
            return [self.scrub(item) for item in data]
        return data

    def scrub_body(self, body: str | None) -> str | None:
        """Scrub a request/response body — handles JSON and plain text."""
        if body is None:
            return None
        try:
            parsed = json.loads(body)
            return json.dumps(self.scrub(parsed))
        except (json.JSONDecodeError, ValueError):
            return self.scrub_string(body)

    @staticmethod
    def truncate_body(body: str | None, max_bytes: int = 51200) -> str | None:
        """Truncate body to max_bytes to prevent huge payloads in the DB."""
        if body is None:
            return None
        encoded = body.encode("utf-8")
        if len(encoded) <= max_bytes:
            return body
        return encoded[:max_bytes].decode("utf-8", errors="ignore") + "\n[TRUNCATED]"
