"""AnalysisResult model — stores analysis execution metadata for reproducibility."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("cases.id", ondelete="CASCADE"), index=True
    )
    executed_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    algorithm_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    configuration_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1.0.0")
    result_summary: Mapped[str] = mapped_column(Text, nullable=False, default="{}")  # JSON
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="completed")
