"""Add anomaly detection fields — folded into 001 for this scaffold.

Revision ID: 003
Revises: 002
Create Date: 2026-01-01
"""
from typing import Sequence, Union

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # anomaly_score / is_anomaly already created in 001_initial_schema.
    # Placeholder for future anomaly-related schema changes.
    pass


def downgrade() -> None:
    pass
