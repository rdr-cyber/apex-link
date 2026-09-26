"""Case model."""

import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class CaseStatus(str, enum.Enum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    ANALYSIS = "ANALYSIS"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"


class CasePriority(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class Case(Base):
    __tablename__ = "cases"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    category: Mapped[str] = mapped_column(String(100), nullable=False, default="UNCATEGORIZED")
    priority: Mapped[CasePriority] = mapped_column(Enum(CasePriority, native_enum=False), default=CasePriority.MEDIUM)
    status: Mapped[CaseStatus] = mapped_column(Enum(CaseStatus, native_enum=False), default=CaseStatus.OPEN)
    incident_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    location: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    assigned_to: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    creator = relationship("User", back_populates="created_cases", foreign_keys=[created_by])
    assignee = relationship("User", back_populates="assigned_cases", foreign_keys=[assigned_to])
    evidence_items = relationship("Evidence", back_populates="case", cascade="all, delete-orphan")
    case_entities = relationship("CaseEntity", back_populates="case", cascade="all, delete-orphan")
    relationships = relationship("Relationship", back_populates="case", foreign_keys="Relationship.case_id")
    leads = relationship("Lead", back_populates="case", foreign_keys="Lead.case_id")
    audit_logs = relationship("AuditLog", back_populates="case")
