"""LangGraph Node 3: Writer — generates pytest code from test scenarios."""

import asyncio
import json
import logging
import os

import anthropic

from langgraph_pipeline.prompts import WRITER_SYSTEM, WRITER_USER, WRITER_RETRY_SYSTEM
from langgraph_pipeline.state import AgentState

logger = logging.getLogger(__name__)
_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
TIMEOUT = int(os.environ.get("LLM_TIMEOUT_SECONDS", "30"))
MAX_TOKENS = int(os.environ.get("LLM_MAX_TOKENS", "2000"))


async def writer_node(state: AgentState) -> AgentState:
    """Generate the actual pytest test code."""
    req = state["request"]

    is_retry = state["retry_count"] > 0 and state.get("error_message")

    if is_retry:
        system_prompt = WRITER_RETRY_SYSTEM.format(
            error_message=state.get("error_message", ""),
            broken_code=state.get("generated_code", ""),
        )
        user_msg = "Fix the code as described in the system prompt."
    else:
        system_prompt = WRITER_SYSTEM
        user_msg = WRITER_USER.format(
            method=req.get("method", ""),
            path=req.get("path", ""),
            request_body=req.get("request_body") or "null",
            response_status=req.get("response_status", 200),
            response_body=str(req.get("response_body", ""))[:1000],
            response_time_ms=req.get("response_time_ms", 0),
            is_anomaly=req.get("is_anomaly", False),
            scenarios_json=json.dumps(state["test_scenarios"], indent=2),
        )

    try:
        response = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(
                None,
                lambda: _client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_msg}],
                ),
            ),
            timeout=TIMEOUT,
        )
        code = response.content[0].text.strip()
        # Strip accidental markdown fences
        if code.startswith("```"):
            lines = code.split("\n")
            code = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        state["generated_code"] = code
    except (asyncio.TimeoutError, Exception) as exc:
        logger.error("Writer failed: %s", exc)
        state["generated_code"] = f"# Writer node failed: {exc}\ndef test_placeholder(): pass\n"
    return state
