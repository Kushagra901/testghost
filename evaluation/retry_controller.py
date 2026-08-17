"""
Controls retry logic for the DeepEval scoring loop.
"""

import os

PASS_THRESHOLD = float(os.environ.get("EVAL_PASS_THRESHOLD", "0.70"))
MAX_RETRIES = int(os.environ.get("EVAL_MAX_RETRIES", "2"))


class RetryController:
    async def should_retry(self, score_result: dict, retry_count: int) -> bool:
        """Return True if the test should be regenerated."""
        overall = score_result.get("overall", 0.0) or 0.0
        return overall < PASS_THRESHOLD and retry_count < MAX_RETRIES

    def build_retry_feedback(self, score_result: dict) -> str:
        """Build a feedback string injected into the Writer retry prompt."""
        from langgraph_pipeline.prompts import VALIDATOR_FEEDBACK_TEMPLATE
        return VALIDATOR_FEEDBACK_TEMPLATE.format(
            coverage=score_result.get("coverage", 0),
            correctness=score_result.get("correctness", 0),
            edge_coverage=score_result.get("edge_coverage", 0),
            overall=score_result.get("overall", 0),
            reasoning=score_result.get("reasoning", "Unknown issue"),
        )
