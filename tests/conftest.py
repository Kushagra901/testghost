"""
TestGhost own test suite conftest.
Provides fixtures for unit and integration tests.
"""

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_requests() -> list[dict]:
    """Load sample captured requests for use in tests."""
    return json.loads((FIXTURES_DIR / "sample_requests.json").read_text())


@pytest.fixture
def normal_request(sample_requests) -> dict:
    return sample_requests[1]  # GET /api/users/42


@pytest.fixture
def auth_request(sample_requests) -> dict:
    return sample_requests[0]  # POST /api/auth/login


@pytest.fixture
def anomalous_request(sample_requests) -> dict:
    return sample_requests[3]  # GET /api/admin/stats (8200ms response time)
