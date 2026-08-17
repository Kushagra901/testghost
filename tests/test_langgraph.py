"""
Tests for the LangGraph validator node (pure logic, no LLM calls).
Classifier/Planner/Writer nodes require ANTHROPIC_API_KEY and are covered
by integration tests only — see tests/integration/ (future).
"""

import pytest

from langgraph_pipeline.nodes.validator import validator_node
from langgraph_pipeline.state import AgentState


def _base_state(code: str, retry_count: int = 0) -> AgentState:
    return {
        "request": {},
        "endpoint_type": "crud",
        "risk_level": "low",
        "test_scenarios": [],
        "generated_code": code,
        "validation_passed": False,
        "retry_count": retry_count,
        "error_message": None,
    }


async def test_validator_passes_valid_python():
    state = _base_state("def test_x():\n    assert 1 == 1\n")
    result = await validator_node(state)
    assert result["validation_passed"] is True
    assert result["error_message"] is None


async def test_validator_flags_syntax_error_for_retry():
    state = _base_state("def test_x(:\n    pass\n", retry_count=0)
    result = await validator_node(state)
    assert result["validation_passed"] is False
    assert result["error_message"] is not None
    assert "SyntaxError" in result["error_message"]


async def test_validator_gives_up_after_max_retries():
    state = _base_state("def test_x(:\n    pass\n", retry_count=2)
    result = await validator_node(state)
    # After max retries, validator marks as passed with a review comment
    assert result["validation_passed"] is True
    assert "NEEDS REVIEW" in result["generated_code"]
