"""Add duplicate detection fields — folded into 001 for this scaffold.

Revision ID: 002
Revises: 001
Create Date: 2026-01-01
"""
from typing import Sequence, Union

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # is_duplicate / duplicate_of_id already created in 001_initial_schema.
    # This migration is a placeholder to match the phased build plan —
    # use it for any future changes to the deduplication schema.
    pass


def downgrade() -> None:
    pass
