"""Add clustering fields — folded into 001 for this scaffold.

Revision ID: 004
Revises: 003
Create Date: 2026-01-01
"""
from typing import Sequence, Union

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # cluster_id / cluster_label already created in 001_initial_schema.
    # Placeholder for future clustering-related schema changes.
    pass


def downgrade() -> None:
    pass
