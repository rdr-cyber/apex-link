"""Relationship model."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class RelationshipType(str, enum.Enum):
    USES_PHONE = "USES_PHONE"
    OWNS_PHONE = "OWNS_PHONE"
    USES_EMAIL = "USES_EMAIL"
    USES_DEVICE = "USES_DEVICE"
    ASSOCIATED_WITH_IP = "ASSOCIATED_WITH_IP"
    USES_UPI = "USES_UPI"
    TRANSFERRED_TO = "TRANSFERRED_TO"
    LOCATED_AT = "LOCATED_AT"
    MEMBER_OF = "MEMBER_OF"
    CONNECTED_TO = "CONNECTED_TO"
    APPEARS_IN_CASE = "APPEARS_IN_CASE"
    MENTIONED_WITH = "MENTIONED_WITH"


class RelationshipBasis(str, enum.Enum):
    """How the relationship was established."""
    EXPLICIT_SOURCE = "EXPLICIT_SOURCE"          # From structured source data
    STRUCTURED_RECORD = "STRUCTURED_RECORD"      # From CDR/transaction import
    TEXTUAL_CO_OCCURRENCE = "TEXTUAL_CO_OCCURRENCE"  # Entities found in same text
    TEMPORAL_ASSOCIATION = "TEMPORAL_ASSOCIATION"  # Time-proximity based
    SHARED_IDENTIFIER = "SHARED_IDENTIFIER"      # Exact same identifier in different context
    CROSS_CASE_LINK = "CROSS_CASE_LINK"          # Detected across cases
    MANUAL = "MANUAL"                            # Investigator-created


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), index=True
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), index=True
    )
    relationship_type: Mapped[RelationshipType] = mapped_column(Enum(RelationshipType, native_enum=False), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    relationship_basis: Mapped[str] = mapped_column(
        String(30), nullable=False, default=RelationshipBasis.TEXTUAL_CO_OCCURRENCE.value
    )
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    source_evidence_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    source_entity = relationship("Entity", back_populates="source_relationships", foreign_keys=[source_entity_id])
    target_entity = relationship("Entity", back_populates="target_relationships", foreign_keys=[target_entity_id])
    case = relationship("Case", back_populates="relationships")
    source_evidence = relationship("Evidence")
