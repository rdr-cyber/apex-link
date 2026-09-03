"""Entity and CaseEntity models."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class EntityType(str, enum.Enum):
    PERSON = "PERSON"
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    IP_ADDRESS = "IP_ADDRESS"
    UPI_ID = "UPI_ID"
    BANK_ACCOUNT = "BANK_ACCOUNT"
    VEHICLE = "VEHICLE"
    DEVICE = "DEVICE"
    LOCATION = "LOCATION"
    ORGANIZATION = "ORGANIZATION"
    SOCIAL_ACCOUNT = "SOCIAL_ACCOUNT"
    URL = "URL"
    CASE_REFERENCE = "CASE_REFERENCE"


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[EntityType] = mapped_column(Enum(EntityType), nullable=False, index=True)
    canonical_value: Mapped[str] = mapped_column(String(1000), nullable=False)
    display_value: Mapped[str] = mapped_column(String(1000), nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(1000), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    case_entities = relationship("CaseEntity", back_populates="entity")
    source_relationships = relationship("Relationship", back_populates="source_entity", foreign_keys="Relationship.source_entity_id")
    target_relationships = relationship("Relationship", back_populates="target_entity", foreign_keys="Relationship.target_entity_id")


class CaseEntity(Base):
    """Links an entity to a case, with optional source evidence and mention context."""
    __tablename__ = "case_entities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), index=True)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("entities.id", ondelete="CASCADE"), index=True)
    source_evidence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="SET NULL"), nullable=True)
    mention_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    case = relationship("Case", back_populates="case_entities")
    entity = relationship("Entity", back_populates="case_entities")
    source_evidence = relationship("Evidence")
