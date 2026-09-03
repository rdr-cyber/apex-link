"""Case schemas."""

import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class CaseCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(default="", max_length=10000)
    category: str = Field(default="UNCATEGORIZED", max_length=100)
    priority: str = Field(default="MEDIUM")
    incident_date: datetime | None = None
    location: str | None = Field(None, max_length=500)
    assigned_to: uuid.UUID | None = None


class CaseUpdate(BaseModel):
    title: str | None = Field(None, max_length=500)
    description: str | None = Field(None, max_length=10000)
    category: str | None = Field(None, max_length=100)
    priority: str | None = None
    status: str | None = None
    incident_date: datetime | None = None
    location: str | None = Field(None, max_length=500)
    assigned_to: uuid.UUID | None = None


class CaseResponse(BaseModel):
    id: uuid.UUID
    case_number: str
    title: str
    description: str
    category: str
    priority: str
    status: str
    incident_date: datetime | None
    location: str | None
    created_by: uuid.UUID
    assigned_to: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CaseListResponse(BaseModel):
    items: list[CaseResponse]
    total: int
    page: int
    page_size: int
