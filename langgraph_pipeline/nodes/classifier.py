"""LangGraph Node 1: Classifier — determines endpoint type and risk level."""

import asyncio
import json
import logging
import os

import anthropic

from langgraph_pipeline.prompts import CLASSIFIER_SYSTEM, CLASSIFIER_USER
from langgraph_pipeline.state import AgentState

logger = logging.getLogger(__name__)
_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
TIMEOUT = int(os.environ.get("LLM_TIMEOUT_SECONDS", "30"))


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
        response = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: _client.messages.create(
                    model=MODEL,
                    max_tokens=200,
                    system=CLASSIFIER_SYSTEM,
                    messages=[{"role": "user", "content": user_msg}],
                ),
            ),
            timeout=TIMEOUT,
        )
        text = response.content[0].text.strip()
        parsed = json.loads(text)
        state["endpoint_type"] = str(parsed.get("endpoint_type", "crud"))
        state["risk_level"] = str(parsed.get("risk_level", "low"))
    except (json.JSONDecodeError, asyncio.TimeoutError, Exception) as exc:
        logger.warning("Classifier failed (%s) — defaulting to crud/low", exc)
        state["endpoint_type"] = "crud"
        state["risk_level"] = "low"

    return state
