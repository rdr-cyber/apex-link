"""Evidence schemas."""

import uuid
from datetime import datetime
from pydantic import BaseModel


class EvidenceResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    evidence_number: str
    evidence_type: str
    filename: str
    mime_type: str
    size_bytes: int
    sha256_hash: str
    description: str
    source: str
    collected_by: str | None
    collected_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class EvidenceListResponse(BaseModel):
    items: list[EvidenceResponse]
    total: int
    page: int
    page_size: int


class IntegrityResponse(BaseModel):
    evidence_id: uuid.UUID
    stored_hash: str
    current_hash: str
    integrity_status: str  # VERIFIED, MISMATCH, UNAVAILABLE
