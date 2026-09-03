"""Add extraction_method to entity_mentions.

Revision ID: 002
Revises: 001
Create Date: 2026-09-03
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "entity_mentions",
        sa.Column("extraction_method", sa.String(20), nullable=False, server_default="REGEX"),
    )
    # Update existing rows to have the default value
    op.execute("UPDATE entity_mentions SET extraction_method = 'REGEX' WHERE extraction_method IS NULL")


def downgrade() -> None:
    op.drop_column("entity_mentions", "extraction_method")
