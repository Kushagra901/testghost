"""
Generation endpoint — orchestrates the full ML + LangGraph pipeline
for a completed session and produces test files + HTML report.
"""

import logging
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import Session, SessionStatus
from backend.db.session import get_db
from backend.schemas.capture import GenerateRequest, GenerateResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/generate", response_model=GenerateResponse)
async def generate(
    body: GenerateRequest, db: AsyncSession = Depends(get_db)
) -> GenerateResponse:
    """
    Run the full generation pipeline for a completed session:
    1. KMeans clustering
    2. LangGraph agent per cluster
    3. DeepEval scoring + retry
    4. File writing
    5. HTML report
    """
    result = await db.execute(select(Session).where(Session.id == body.session_id))
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == SessionStatus.ACTIVE:
        raise HTTPException(
            status_code=409,
            detail="Session is still active. Call /session/stop first.",
        )

    output_dir = os.environ.get("OUTPUT_DIR", "output")

    # Step 1: cluster
    from ml.clusterer import cluster_session
    cluster_map = await cluster_session(body.session_id, db)
    logger.info("Clustering complete: %s clusters", len(cluster_map))

    # Step 2–4: generate + evaluate per cluster
    from backend.db.models import CapturedRequest, GeneratedTest
    from evaluation.grader import TestGrader
    from evaluation.retry_controller import RetryController
    from generation.conftest_writer import write_conftest
    from generation.file_writer import write_test_file
    from langgraph_pipeline.graph import test_generation_graph

    grader = TestGrader()
    retry_ctrl = RetryController()
    test_files: list[str] = []

    for cluster_id, cluster_label in cluster_map.items():
        req_result = await db.execute(
            select(CapturedRequest)
            .where(CapturedRequest.session_id == body.session_id)
            .where(CapturedRequest.cluster_id == cluster_id)
            .where(CapturedRequest.is_duplicate == False)  # noqa: E712
        )
        requests = req_result.scalars().all()
        if not requests:
            continue

        for req in requests:
            state = {
                "request": {
                    "method": req.method,
                    "path": req.path,
                    "url": req.url,
                    "request_body": req.request_body,
                    "response_status": req.response_status,
                    "response_body": req.response_body,
                    "response_time_ms": req.response_time_ms,
                    "is_anomaly": req.is_anomaly,
                },
                "endpoint_type": "",
                "risk_level": "",
                "test_scenarios": [],
                "generated_code": "",
                "validation_passed": False,
                "retry_count": 0,
                "error_message": None,
            }

            retry_count = 0
            score_result: dict = {}

            while retry_count <= 2:
                result_state = await test_generation_graph.ainvoke(state)
                generated_code: str = result_state.get("generated_code", "")

                score_result = grader.score(
                    generated_code,
                    state["request"],
                    {"status": req.response_status, "body": req.response_body},
                )

                if not await retry_ctrl.should_retry(score_result, retry_count):
                    break

                feedback = retry_ctrl.build_retry_feedback(score_result)
                state["generated_code"] = generated_code
                state["error_message"] = feedback
                state["retry_count"] = retry_count + 1
                retry_count += 1

            file_path = write_test_file(cluster_label, generated_code, output_dir)
            if file_path not in test_files:
                test_files.append(file_path)

            gt = GeneratedTest(
                session_id=body.session_id,
                cluster_label=cluster_label,
                file_path=file_path,
                code=generated_code,
                score_coverage=score_result.get("coverage"),
                score_correctness=score_result.get("correctness"),
                score_edge_coverage=score_result.get("edge_coverage"),
                score_overall=score_result.get("overall"),
                retry_count=retry_count,
                is_high_confidence=(score_result.get("overall", 0) or 0) >= 0.9,
                needs_review=(score_result.get("overall", 0) or 0) < 0.5,
            )
            db.add(gt)

    write_conftest(list(cluster_map.values()), "http://localhost:8000", output_dir)

    # Step 5: report
    from reporting.reporter import ReportGenerator
    reporter = ReportGenerator()
    report_path = await reporter.generate(body.session_id, db, output_dir)

    await db.commit()

    return GenerateResponse(
        session_id=body.session_id,
        report_path=report_path,
        test_files=test_files,
        summary={
            "clusters": len(cluster_map),
            "test_files": len(test_files),
            "cluster_labels": list(cluster_map.values()),
        },
    )
