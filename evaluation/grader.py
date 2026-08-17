"""
DeepEval-based test quality grader for TestGhost.
Scores every generated pytest file on Coverage, Correctness, and EdgeCoverage.
"""

import ast
import json
import logging
import os

logger = logging.getLogger(__name__)

PASS_THRESHOLD = float(os.environ.get("EVAL_PASS_THRESHOLD", "0.70"))


class TestGrader:
    """
    Scores generated pytest code on three dimensions.
    Does NOT require DeepEval API for correctness checks (AST-based).
    Uses LLM-as-judge only for coverage scoring.
    """

    def score(
        self,
        generated_code: str,
        original_request: dict,
        original_response: dict,
    ) -> dict:
        """
        Returns:
            {coverage, correctness, edge_coverage, overall, reasoning}
        """
        correctness, correctness_reason = self._score_correctness(generated_code)
        edge_coverage, edge_reason = self._score_edge_coverage(generated_code)
        coverage, coverage_reason = self._score_coverage(
            generated_code, original_request, original_response
        )

        overall = (coverage + correctness + edge_coverage) / 3.0
        reasoning = f"Coverage: {coverage_reason} | Correctness: {correctness_reason} | Edge: {edge_reason}"

        logger.info(
            "Test scores — coverage=%.2f correctness=%.2f edge=%.2f overall=%.2f",
            coverage, correctness, edge_coverage, overall,
        )

        return {
            "coverage": round(coverage, 3),
            "correctness": round(correctness, 3),
            "edge_coverage": round(edge_coverage, 3),
            "overall": round(overall, 3),
            "reasoning": reasoning,
        }

    def _score_correctness(self, code: str) -> tuple[float, str]:
        """AST-based: passes syntax check AND has at least 2 assert statements."""
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return 0.0, f"SyntaxError: {exc}"

        asserts = [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        if len(asserts) == 0:
            return 0.2, "No assert statements found"
        if len(asserts) == 1:
            return 0.6, "Only 1 assert statement (need >= 2)"

        # Check if status code is asserted
        code_lower = code.lower()
        has_status_assert = any(
            kw in code_lower for kw in ["status_code", ".status", "response.status", "assert 200", "assert 201"]
        )
        if not has_status_assert:
            return 0.7, f"{len(asserts)} asserts but no status code assertion"

        return 1.0, f"{len(asserts)} asserts including status code"

    def _score_edge_coverage(self, code: str) -> tuple[float, str]:
        """Check if at least one non-200 status code is tested."""
        error_codes = ["400", "401", "403", "404", "422", "500"]
        code_lower = code.lower()
        found = [c for c in error_codes if c in code_lower]

        if not found:
            return 0.3, "No error status codes tested"
        if len(found) == 1:
            return 0.7, f"Tests status {found[0]}"
        return 1.0, f"Tests multiple error codes: {found}"

    def _score_coverage(
        self, code: str, request: dict, response: dict
    ) -> tuple[float, str]:
        """Check if response fields from the real response are asserted."""
        response_body = response.get("body") or ""
        try:
            parsed = json.loads(response_body)
            if isinstance(parsed, dict):
                fields = list(parsed.keys())
            else:
                fields = []
        except (json.JSONDecodeError, ValueError):
            fields = []

        if not fields:
            return 0.8, "No JSON response fields to check (non-JSON response)"

        covered = [f for f in fields if f in code]
        ratio = len(covered) / len(fields)

        if ratio == 0:
            return 0.2, f"None of {len(fields)} response fields asserted"
        if ratio < 0.5:
            return 0.5, f"{len(covered)}/{len(fields)} response fields asserted"
        return min(1.0, 0.7 + ratio * 0.3), f"{len(covered)}/{len(fields)} response fields asserted"
