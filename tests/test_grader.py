"""Tests for the DeepEval-based test grader."""

from evaluation.grader import TestGrader
from evaluation.retry_controller import RetryController


GOOD_TEST_CODE = '''
import pytest

@pytest.mark.parametrize("case", [
    {"name": "happy_path", "expected_status": 200},
])
def test_get_user(client, case):
    """Test GET /api/users/42 happy path and error cases."""
    response = client.get("/api/users/42")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 42
    assert data["name"] == "Test User"

    response_404 = client.get("/api/users/99999")
    assert response_404.status_code == 404
'''

BAD_TEST_CODE = '''
def test_get_user(client):
    response = client.get("/api/users/42")
'''

BROKEN_SYNTAX_CODE = '''
def test_get_user(client:
    response = client.get("/api/users/42")
'''


def test_grader_scores_good_code_highly():
    grader = TestGrader()
    result = grader.score(
        GOOD_TEST_CODE,
        {"method": "GET", "path": "/api/users/42"},
        {"status": 200, "body": '{"id": 42, "name": "Test User"}'},
    )
    assert result["overall"] >= 0.7, f"Good test scored too low: {result}"


def test_grader_scores_bad_code_low():
    grader = TestGrader()
    result = grader.score(
        BAD_TEST_CODE,
        {"method": "GET", "path": "/api/users/42"},
        {"status": 200, "body": '{"id": 42, "name": "Test User"}'},
    )
    assert result["overall"] < 0.7, f"Bad test (no asserts) scored too high: {result}"


def test_grader_rejects_broken_syntax():
    grader = TestGrader()
    result = grader.score(
        BROKEN_SYNTAX_CODE,
        {"method": "GET", "path": "/api/users/42"},
        {"status": 200, "body": "{}"},
    )
    assert result["correctness"] == 0.0


async def test_retry_controller_triggers_on_low_score():
    controller = RetryController()
    low_score = {"overall": 0.4}
    assert await controller.should_retry(low_score, retry_count=0) is True
    assert await controller.should_retry(low_score, retry_count=2) is False


async def test_retry_controller_skips_on_high_score():
    controller = RetryController()
    high_score = {"overall": 0.95}
    assert await controller.should_retry(high_score, retry_count=0) is False
