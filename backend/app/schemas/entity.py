"""Entity schemas."""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class EntityCreate(BaseModel):
    entity_type: str
    canonical_value: str = Field(..., min_length=1, max_length=1000)
    display_value: str = Field(..., min_length=1, max_length=1000)
    normalized_value: str = Field(..., min_length=1, max_length=1000)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class EntityResponse(BaseModel):
    id: uuid.UUID
    entity_type: str
    canonical_value: str
    display_value: str
    normalized_value: str
    confidence: float
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class EntityListResponse(BaseModel):
    items: list[EntityResponse]
    total: int
    page: int
    page_size: int


class CaseEntityResponse(BaseModel):
    id: uuid.UUID
    case_id: uuid.UUID
    entity_id: uuid.UUID
    source_evidence_id: uuid.UUID | None
    mention_text: str
    confidence: float
    created_at: datetime
    entity: EntityResponse | None = None

    class Config:
        from_attributes = True


class ExtractedEntity(BaseModel):
    entity_type: str
    raw_text: str
    normalized_value: str
    confidence: float


class ExtractionResponse(BaseModel):
    evidence_id: uuid.UUID
    extracted_entities: list[ExtractedEntity]
    total_extracted: int
    total_new: int
    total_linked: int
