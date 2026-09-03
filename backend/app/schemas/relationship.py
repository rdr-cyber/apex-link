"""Relationship schemas."""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class RelationshipCreate(BaseModel):
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relationship_type: str
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_evidence_id: uuid.UUID | None = None
    description: str = ""


class RelationshipResponse(BaseModel):
    id: uuid.UUID
    source_entity_id: uuid.UUID
    target_entity_id: uuid.UUID
    relationship_type: str
    confidence: float
    case_id: uuid.UUID
    source_evidence_id: uuid.UUID | None
    description: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RelationshipListResponse(BaseModel):
    items: list[RelationshipResponse]
    total: int


class GraphNode(BaseModel):
    id: str
    label: str
    entity_type: str
    confidence: float
    degree: float = 0.0
    betweenness: float = 0.0
    closeness: float = 0.0
    cases: list[str] = []


class GraphEdge(BaseModel):
    id: str
    source: str
    target: str
    relationship_type: str
    confidence: float
    label: str


class GraphResponse(BaseModel):
    nodes: list[GraphNode]
    edges: list[GraphEdge]
    stats: dict
