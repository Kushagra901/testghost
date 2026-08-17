"""
HTML report generator for TestGhost.
Produces a single self-contained HTML file — no external dependencies.
"""

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import CapturedRequest, GeneratedTest, Session

logger = logging.getLogger(__name__)
TEMPLATES_DIR = Path(__file__).parent / "templates"


class ReportGenerator:
    def __init__(self) -> None:
        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=True,
        )

    async def generate(
        self, session_id: uuid.UUID, db: AsyncSession, output_dir: str
    ) -> str:
        """Build and write the HTML report. Returns the file path."""
        # Load session
        sess_result = await db.execute(select(Session).where(Session.id == session_id))
        session = sess_result.scalar_one_or_none()
        if session is None:
            raise ValueError(f"Session {session_id} not found")

        # Load requests
        req_result = await db.execute(
            select(CapturedRequest)
            .where(CapturedRequest.session_id == session_id)
            .order_by(CapturedRequest.cluster_label, CapturedRequest.created_at)
        )
        requests = req_result.scalars().all()

        # Load generated tests
        test_result = await db.execute(
            select(GeneratedTest)
            .where(GeneratedTest.session_id == session_id)
            .order_by(GeneratedTest.cluster_label)
        )
        tests = test_result.scalars().all()

        # Compute stats
        total = len(requests)
        unique = sum(1 for r in requests if not r.is_duplicate)
        duplicates = total - unique
        anomalies = sum(1 for r in requests if r.is_anomaly)

        # Group by cluster
        clusters: dict[str, dict] = {}
        for r in requests:
            label = r.cluster_label or "general"
            if label not in clusters:
                clusters[label] = {"requests": [], "tests": []}
            clusters[label]["requests"].append(r)

        for t in tests:
            label = t.cluster_label or "general"
            if label not in clusters:
                clusters[label] = {"requests": [], "tests": []}
            clusters[label]["tests"].append(t)

        scores = [t.score_overall for t in tests if t.score_overall is not None]
        avg_score = sum(scores) / len(scores) if scores else 0.0

        context = {
            "session": session,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "total_captured": total,
            "unique_endpoints": unique,
            "duplicate_count": duplicates,
            "anomaly_count": anomalies,
            "test_count": len(tests),
            "avg_score": round(avg_score, 3),
            "clusters": clusters,
            "tests": tests,
        }

        template = self._env.get_template("report.html")
        html = template.render(**context)

        reports_dir = Path(output_dir) / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        report_path = reports_dir / f"report_{session_id}.html"
        report_path.write_text(html, encoding="utf-8")

        logger.info("Report written to %s", report_path)
        return str(report_path)
