"""EntityMention model — stores raw extracted mentions from evidence text."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.entity import EntityType


class ExtractionMethod(str, enum.Enum):
    REGEX = "REGEX"
    NLP = "NLP"
    MANUAL = "MANUAL"
    IMPORT = "IMPORT"
    AI_ASSISTED = "AI_ASSISTED"


class EntityMention(Base):
    __tablename__ = "entity_mentions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE"), index=True
    )
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_value: Mapped[str] = mapped_column(String(1000), nullable=False)
    start_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    extraction_method: Mapped[str] = mapped_column(String(20), nullable=False, default=ExtractionMethod.REGEX.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationships
    evidence = relationship("Evidence", back_populates="entity_mentions")
