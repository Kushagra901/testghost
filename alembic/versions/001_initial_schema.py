"""Initial schema — sessions, captured_requests, embeddings, generated_tests

Revision ID: 001
Revises:
Create Date: 2026-01-01
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import UUID

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.Enum("active", "complete", name="sessionstatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "captured_requests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.Text, nullable=False),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("request_headers", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("request_body", sa.Text, nullable=True),
        sa.Column("response_status", sa.Integer, nullable=False),
        sa.Column("response_body", sa.Text, nullable=True),
        sa.Column("response_headers", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("response_time_ms", sa.Float, nullable=True),
        sa.Column("is_duplicate", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("duplicate_of_id", UUID(as_uuid=True), nullable=True),
        sa.Column("anomaly_score", sa.Float, nullable=True),
        sa.Column("is_anomaly", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("cluster_id", sa.Integer, nullable=True),
        sa.Column("cluster_label", sa.String(100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_captured_requests_session_id", "captured_requests", ["session_id"])

    op.create_table(
        "embeddings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("captured_request_id", UUID(as_uuid=True),
                   sa.ForeignKey("captured_requests.id", ondelete="CASCADE"), nullable=False),
        sa.Column("vector", Vector(384), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("captured_request_id", name="uq_embedding_request"),
    )
    op.execute(
        "CREATE INDEX ix_embeddings_vector ON embeddings USING ivfflat (vector vector_cosine_ops) WITH (lists = 100)"
    )

    op.create_table(
        "generated_tests",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("cluster_label", sa.String(100), nullable=False),
        sa.Column("file_path", sa.Text, nullable=False),
        sa.Column("code", sa.Text, nullable=False),
        sa.Column("score_coverage", sa.Float, nullable=True),
        sa.Column("score_correctness", sa.Float, nullable=True),
        sa.Column("score_edge_coverage", sa.Float, nullable=True),
        sa.Column("score_overall", sa.Float, nullable=True),
        sa.Column("retry_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("is_high_confidence", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("needs_review", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("generated_tests")
    op.drop_table("embeddings")
    op.drop_table("captured_requests")
    op.drop_table("sessions")
    op.execute("DROP TYPE IF EXISTS sessionstatus")
