"""AgentState for the LangGraph test generation pipeline."""

from typing import TypedDict


class AgentState(TypedDict):
    """Mutable state passed between all 4 LangGraph nodes."""
    request: dict                    # full captured request+response data
    endpoint_type: str               # auth | crud | admin | webhook | public
    risk_level: str                  # high | medium | low
    test_scenarios: list[dict]       # [{name, type, expected_status, description}]
    generated_code: str              # full pytest file as a string
    validation_passed: bool          # True when ast.parse succeeds
    retry_count: int                 # how many times Writer has been retried
    error_message: str | None        # syntax error or eval feedback for retry
