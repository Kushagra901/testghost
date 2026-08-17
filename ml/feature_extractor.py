"""
Feature extraction for the Isolation Forest anomaly detector.
Extracts exactly 6 normalized floats from a CapturedRequest.
"""

import json


def _json_depth(obj: object, current: int = 0) -> int:
    """Recursively compute max nesting depth of a JSON object."""
    if isinstance(obj, dict):
        if not obj:
            return current
        return max(_json_depth(v, current + 1) for v in obj.values())
    if isinstance(obj, list):
        if not obj:
            return current
        return max(_json_depth(item, current + 1) for item in obj)
    return current


def extract_features(request: object) -> list[float]:
    """
    Extract 6 normalized features from a CapturedRequest ORM object.

    Features:
      0. response_time_ms  (capped at 10000ms → 0.0–1.0)
      1. response_body_size in bytes (capped at 100000 → 0.0–1.0)
      2. response_status_normalized (100–599 → 0.0–1.0)
      3. json_field_count (top-level keys, capped at 50 → 0.0–1.0)
      4. json_nesting_depth (capped at 10 → 0.0–1.0)
      5. content_type_score (json=1.0, html=0.5, other=0.0)
    """
    response_time_ms: float = getattr(request, "response_time_ms", None) or 0.0
    response_body: str | None = getattr(request, "response_body", None)
    response_status: int = getattr(request, "response_status", 200) or 200
    response_headers: dict = getattr(request, "response_headers", {}) or {}

    # Feature 0: response time
    f0 = min(response_time_ms, 10000.0) / 10000.0

    # Feature 1: body size
    body_bytes = len((response_body or "").encode("utf-8"))
    f1 = min(body_bytes, 100_000) / 100_000.0

    # Feature 2: status code
    f2 = (min(max(response_status, 100), 599) - 100) / 499.0

    # Feature 3 + 4: JSON analysis
    f3, f4 = 0.0, 0.0
    if response_body:
        try:
            parsed = json.loads(response_body)
            if isinstance(parsed, dict):
                f3 = min(len(parsed), 50) / 50.0
                f4 = min(_json_depth(parsed), 10) / 10.0
            elif isinstance(parsed, list):
                f3 = min(len(parsed), 50) / 50.0
        except (json.JSONDecodeError, ValueError):
            pass

    # Feature 5: content type
    content_type: str = ""
    for key, val in response_headers.items():
        if key.lower() == "content-type":
            content_type = str(val).lower()
            break
    if "application/json" in content_type:
        f5 = 1.0
    elif "text/html" in content_type:
        f5 = 0.5
    else:
        f5 = 0.0

    return [f0, f1, f2, f3, f4, f5]
