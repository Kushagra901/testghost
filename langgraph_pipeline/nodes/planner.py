"""LangGraph Node 2: Planner — creates test scenarios from endpoint classification."""

import asyncio
import json
import logging
import os

from langgraph_pipeline.llm import call_llm
from langgraph_pipeline.prompts import PLANNER_SYSTEM, PLANNER_USER
from langgraph_pipeline.state import AgentState

logger = logging.getLogger(__name__)


async def planner_node(state: AgentState) -> AgentState:
    """Generate structured test scenarios for the Writer node."""
    req = state["request"]
    user_msg = PLANNER_USER.format(
        endpoint_type=state["endpoint_type"],
        risk_level=state["risk_level"],
        method=req.get("method", ""),
        path=req.get("path", ""),
        request_body=str(req.get("request_body", ""))[:300],
        response_status=req.get("response_status", 200),
        response_body_preview=str(req.get("response_body", ""))[:300],
    )

    try:
        text = await call_llm(PLANNER_SYSTEM, user_msg, max_tokens=500)
        # Strip markdown fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        scenarios = json.loads(text)
        if not isinstance(scenarios, list):
            scenarios = []
        state["test_scenarios"] = scenarios
    except (json.JSONDecodeError, asyncio.TimeoutError, Exception) as exc:
        logger.warning("Planner failed (%s) — using default scenarios", exc)
        state["test_scenarios"] = [
            {"name": "test_happy_path", "type": "happy_path",
             "expected_status": req.get("response_status", 200), "description": "Normal request"},
            {"name": "test_missing_field", "type": "missing_required_field",
             "expected_status": 400, "description": "Missing required field"},
        ]
    return state
