"""Lead schemas."""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class LeadResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    related_case_id: uuid.UUID | None
    lead_type: str
    score: float
    priority: str
    explanation: str
    status: str
    factors: str  # JSON string
    created_at: datetime
    reviewed_by: uuid.UUID | None
    reviewed_at: datetime | None

    class Config:
        from_attributes = True


class LeadUpdate(BaseModel):
    status: str = Field(..., pattern="^(REVIEWING|CONFIRMED|DISMISSED)$")


class LeadListResponse(BaseModel):
    items: list[LeadResponse]
    total: int
    page: int
    page_size: int
