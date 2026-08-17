"""Tests for the PII scrubber and feature extractor."""

from proxy.scrubber import PIIScrubber
from ml.feature_extractor import extract_features


def test_scrubber_removes_email():
    scrubber = PIIScrubber()
    result = scrubber.scrub_string("Contact us at user@example.com for help")
    assert "[SCRUBBED_EMAIL]" in result
    assert "user@example.com" not in result


def test_scrubber_removes_jwt():
    scrubber = PIIScrubber()
    jwt = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0In0.SflKxwRJSMeKKF2QT4fwpMeJf"
    result = scrubber.scrub_string(f"Bearer {jwt}")
    assert "eyJ" not in result


def test_scrubber_truncates_large_body():
    scrubber = PIIScrubber()
    large = "x" * 100_000
    result = scrubber.truncate_body(large, max_bytes=51200)
    assert result is not None
    assert "[TRUNCATED]" in result
    assert len(result.encode("utf-8")) <= 52000  # small buffer


def test_feature_extraction_returns_six_floats(normal_request):
    class FakeRequest:
        response_time_ms = 88.1
        response_body = '{"id": 42, "name": "Test User"}'
        response_status = 200
        response_headers = {"content-type": "application/json"}

    features = extract_features(FakeRequest())
    assert len(features) == 6
    assert all(0.0 <= f <= 1.0 for f in features), f"Features out of range: {features}"


def test_feature_extraction_anomalous_response(anomalous_request):
    class FakeRequest:
        response_time_ms = 8200.0
        response_body = '{"total_users": 1500}'
        response_status = 200
        response_headers = {"content-type": "application/json"}

    features = extract_features(FakeRequest())
    # f0 = response_time/10000 = 0.82 — should be high
    assert features[0] > 0.5, "Slow response should produce high feature 0"
