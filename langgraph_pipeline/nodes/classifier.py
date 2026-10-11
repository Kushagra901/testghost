"""LangGraph Node 1: Classifier — determines endpoint type and risk level."""

import asyncio
import json
import logging
import os

from langgraph_pipeline.llm import call_llm
from langgraph_pipeline.prompts import CLASSIFIER_SYSTEM, CLASSIFIER_USER
from langgraph_pipeline.state import AgentState

logger = logging.getLogger(__name__)


async def classifier_node(state: AgentState) -> AgentState:
    """Classify the endpoint type and risk level."""
    req = state["request"]
    user_msg = CLASSIFIER_USER.format(
        method=req.get("method", ""),
        path=req.get("path", ""),
        request_body=str(req.get("request_body", ""))[:500],
        response_status=req.get("response_status", 200),
        response_body_preview=str(req.get("response_body", ""))[:500],
    )

    try:
        text = await call_llm(CLASSIFIER_SYSTEM, user_msg, max_tokens=200)
        # Strip markdown fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        parsed = json.loads(text)
        state["endpoint_type"] = str(parsed.get("endpoint_type", "crud"))
        state["risk_level"] = str(parsed.get("risk_level", "low"))
    except (json.JSONDecodeError, asyncio.TimeoutError, Exception) as exc:
        logger.warning("Classifier failed (%s) — defaulting to crud/low", exc)
        state["endpoint_type"] = "crud"
        state["risk_level"] = "low"

    return state
