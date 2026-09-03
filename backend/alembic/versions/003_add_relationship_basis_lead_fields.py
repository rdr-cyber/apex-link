"""Add relationship_basis, lead review_notes and analysis_id.

Revision ID: 003
Revises: 002
Create Date: 2026-09-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add relationship_basis to relationships
    op.add_column(
        "relationships",
        sa.Column("relationship_basis", sa.String(30), nullable=False, server_default="TEXTUAL_CO_OCCURRENCE"),
    )

    # Add review_notes and analysis_id to leads
    op.add_column(
        "leads",
        sa.Column("review_notes", sa.Text, nullable=False, server_default=""),
    )
    op.add_column(
        "leads",
        sa.Column("analysis_id", sa.String(36), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("leads", "analysis_id")
    op.drop_column("leads", "review_notes")
    op.drop_column("relationships", "relationship_basis")
