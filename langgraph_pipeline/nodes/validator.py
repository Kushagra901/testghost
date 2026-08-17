"""LangGraph Node 4: Validator — checks generated code for syntax validity."""

import ast
import logging

from langgraph_pipeline.state import AgentState

logger = logging.getLogger(__name__)
MAX_RETRIES = 2


async def validator_node(state: AgentState) -> AgentState:
    """Parse the generated test code. Flag invalid code for retry."""
    code = state.get("generated_code", "")

    try:
        ast.parse(code)
        state["validation_passed"] = True
        state["error_message"] = None
        logger.debug("Validator: syntax OK")
    except SyntaxError as exc:
        retry_count = state.get("retry_count", 0)
        if retry_count < MAX_RETRIES:
            state["validation_passed"] = False
            state["error_message"] = f"SyntaxError at line {exc.lineno}: {exc.msg}"
            logger.warning("Validator: syntax error (retry %d) — %s", retry_count, exc.msg)
        else:
            # Give up — mark as needs review
            state["validation_passed"] = True
            needs_review_comment = f"# NEEDS REVIEW: syntax validation failed after {MAX_RETRIES} retries\n# Error: {exc}\n"
            state["generated_code"] = needs_review_comment + code
            state["error_message"] = str(exc)
            logger.error("Validator: max retries reached — marking for review")

    return state
