"""Initial migration — create all tables.

Revision ID: 001
Revises:
Create Date: 2026-01-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False, index=True),
        sa.Column("password_hash", sa.Text, nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, default="INVESTIGATOR"),
        sa.Column("is_active", sa.Boolean, nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Cases
    op.create_table(
        "cases",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_number", sa.String(32), unique=True, nullable=False, index=True),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False, default=""),
        sa.Column("category", sa.String(100), nullable=False, default="UNCATEGORIZED"),
        sa.Column("priority", sa.String(20), nullable=False, default="MEDIUM"),
        sa.Column("status", sa.String(20), nullable=False, default="OPEN"),
        sa.Column("incident_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("location", sa.String(500), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Evidence
    op.create_table(
        "evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="CASCADE"), index=True),
        sa.Column("evidence_number", sa.String(32), unique=True, nullable=False),
        sa.Column("evidence_type", sa.String(30), nullable=False),
        sa.Column("filename", sa.String(500), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False, default=0),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("description", sa.Text, nullable=False, default=""),
        sa.Column("source", sa.String(500), nullable=False, default="unknown"),
        sa.Column("collected_by", sa.String(255), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Entities
    op.create_table(
        "entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(30), nullable=False, index=True),
        sa.Column("canonical_value", sa.String(1000), nullable=False),
        sa.Column("display_value", sa.String(1000), nullable=False),
        sa.Column("normalized_value", sa.String(1000), nullable=False, index=True),
        sa.Column("confidence", sa.Float, nullable=False, default=1.0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Case Entities
    op.create_table(
        "case_entities",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="CASCADE"), index=True),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id", ondelete="CASCADE"), index=True),
        sa.Column("source_evidence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True),
        sa.Column("mention_text", sa.Text, nullable=False, default=""),
        sa.Column("confidence", sa.Float, nullable=False, default=1.0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Entity Mentions
    op.create_table(
        "entity_mentions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("evidence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evidence.id", ondelete="CASCADE"), index=True),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("raw_text", sa.Text, nullable=False),
        sa.Column("normalized_value", sa.String(1000), nullable=False),
        sa.Column("start_offset", sa.Integer, nullable=True),
        sa.Column("end_offset", sa.Integer, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False, default=0.0),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Relationships
    op.create_table(
        "relationships",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id", ondelete="CASCADE"), index=True),
        sa.Column("target_entity_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("entities.id", ondelete="CASCADE"), index=True),
        sa.Column("relationship_type", sa.String(30), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False, default=1.0),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="CASCADE"), index=True),
        sa.Column("source_evidence_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True),
        sa.Column("description", sa.Text, nullable=False, default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Leads
    op.create_table(
        "leads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="CASCADE"), index=True),
        sa.Column("related_case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="SET NULL"), nullable=True),
        sa.Column("lead_type", sa.String(50), nullable=False),
        sa.Column("score", sa.Float, nullable=False, default=0.0),
        sa.Column("priority", sa.String(20), nullable=False, default="LOW"),
        sa.Column("explanation", sa.Text, nullable=False, default=""),
        sa.Column("status", sa.String(20), nullable=False, default="NEW"),
        sa.Column("factors", sa.Text, nullable=False, default="[]"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Audit Logs
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("action", sa.String(100), nullable=False, index=True),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("resource_id", sa.String(100), nullable=True),
        sa.Column("details", sa.Text, nullable=False, default=""),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="SET NULL"), nullable=True),
    )

    # Analysis Results
    op.create_table(
        "analysis_results",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cases.id", ondelete="CASCADE"), index=True),
        sa.Column("executed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("algorithm_version", sa.String(32), nullable=False, default="1.0.0"),
        sa.Column("configuration_version", sa.String(32), nullable=False, default="1.0.0"),
        sa.Column("result_summary", sa.Text, nullable=False, default="{}"),
        sa.Column("status", sa.String(20), nullable=False, default="completed"),
    )


def downgrade() -> None:
    op.drop_table("analysis_results")
    op.drop_table("audit_logs")
    op.drop_table("leads")
    op.drop_table("relationships")
    op.drop_table("entity_mentions")
    op.drop_table("case_entities")
    op.drop_table("entities")
    op.drop_table("evidence")
    op.drop_table("cases")
    op.drop_table("users")
