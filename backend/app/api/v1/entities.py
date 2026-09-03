"""Entity routes — list, detail, cases, evidence, relationships, timeline."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.entity import Entity, CaseEntity
from app.models.evidence import Evidence
from app.models.relationship import Relationship
from app.models.entity_mention import EntityMention
from app.repositories.entity_repo import EntityRepository
from app.schemas.entity import EntityResponse, EntityListResponse
from app.services.normalization import normalize_phone, normalize_email, normalize_ip, normalize_upi

router = APIRouter(prefix="/entities", tags=["Entities"])


def _normalize_search_query(query: str) -> str:
    """Normalize a search query so +91 9876543210 finds 9876543210."""
    # Try phone normalization
    phone_norm = normalize_phone(query)
    if phone_norm and len(phone_norm) == 10:
        return phone_norm
    # Try email normalization
    if "@" in query:
        return normalize_email(query)
    # Try IP normalization
    ip_norm = normalize_ip(query)
    if ip_norm:
        return ip_norm
    # Try UPI normalization
    if "@" in query and "." not in query.split("@")[-1]:
        return normalize_upi(query)
    return query


@router.get("", response_model=EntityListResponse)
async def list_entities(
    query: str | None = Query(None),
    entity_type: str | None = Query(None),
    normalized_value: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search and list entities. Search normalizes phone/email/IP/UPI queries."""
    repo = EntityRepository(db)
    skip = (page - 1) * page_size

    # Normalize search query
    search_query = query
    if query:
        search_query = _normalize_search_query(query)

    items, total = await repo.search(
        query=search_query, entity_type=entity_type, normalized_value=normalized_value,
        skip=skip, limit=page_size
    )
    return EntityListResponse(
        items=[EntityResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{entity_id}", response_model=EntityResponse)
async def get_entity(
    entity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get an entity by ID."""
    repo = EntityRepository(db)
    entity = await repo.get_by_id(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found.")
    return EntityResponse.model_validate(entity)


@router.get("/{entity_id}/cases")
async def get_entity_cases(
    entity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all cases this entity appears in."""
    repo = EntityRepository(db)
    entity = await repo.get_by_id(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found.")

    stmt = (
        select(CaseEntity)
        .where(CaseEntity.entity_id == entity_id)
        .order_by(desc(CaseEntity.created_at))
    )
    result = await db.execute(stmt)
    case_entities = result.scalars().all()

    return {
        "entity_id": str(entity_id),
        "entity_type": entity.entity_type,
        "display_value": entity.display_value,
        "cases": [
            {
                "case_entity_id": str(ce.id),
                "case_id": str(ce.case_id),
                "source_evidence_id": str(ce.source_evidence_id) if ce.source_evidence_id else None,
                "mention_text": ce.mention_text,
                "confidence": ce.confidence,
                "first_seen": ce.created_at.isoformat() if ce.created_at else None,
            }
            for ce in case_entities
        ],
        "total_cases": len(case_entities),
    }


@router.get("/{entity_id}/evidence")
async def get_entity_evidence(
    entity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all evidence items referencing this entity."""
    repo = EntityRepository(db)
    entity = await repo.get_by_id(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found.")

    stmt = (
        select(EntityMention)
        .where(EntityMention.normalized_value == entity.normalized_value)
        .order_by(desc(EntityMention.created_at))
    )
    result = await db.execute(stmt)
    mentions = result.scalars().all()

    # Deduplicate by evidence_id
    evidence_map: dict[uuid.UUID, list] = {}
    for m in mentions:
        if m.evidence_id not in evidence_map:
            evidence_map[m.evidence_id] = []
        evidence_map[m.evidence_id].append({
            "mention_id": str(m.id),
            "raw_text": m.raw_text,
            "confidence": m.confidence,
            "extraction_method": m.extraction_method,
        })

    return {
        "entity_id": str(entity_id),
        "evidence_count": len(evidence_map),
        "evidence": [
            {"evidence_id": str(eid), "mentions": mentions_list}
            for eid, mentions_list in evidence_map.items()
        ],
    }


@router.get("/{entity_id}/relationships")
async def get_entity_relationships(
    entity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all relationships involving this entity."""
    repo = EntityRepository(db)
    entity = await repo.get_by_id(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found.")

    stmt = (
        select(Relationship)
        .where(
            (Relationship.source_entity_id == entity_id) | (Relationship.target_entity_id == entity_id)
        )
        .order_by(desc(Relationship.created_at))
    )
    result = await db.execute(stmt)
    relationships = result.scalars().all()

    return {
        "entity_id": str(entity_id),
        "relationship_count": len(relationships),
        "relationships": [
            {
                "id": str(r.id),
                "source_entity_id": str(r.source_entity_id),
                "target_entity_id": str(r.target_entity_id),
                "relationship_type": r.relationship_type.value if hasattr(r.relationship_type, 'value') else r.relationship_type,
                "confidence": r.confidence,
                "case_id": str(r.case_id),
                "description": r.description,
            }
            for r in relationships
        ],
    }


@router.get("/{entity_id}/timeline")
async def get_entity_timeline(
    entity_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a timeline of events involving this entity."""
    repo = EntityRepository(db)
    entity = await repo.get_by_id(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found.")

    # Get all mentions of this entity
    stmt = (
        select(EntityMention)
        .where(EntityMention.normalized_value == entity.normalized_value)
        .order_by(desc(EntityMention.created_at))
    )
    result = await db.execute(stmt)
    mentions = result.scalars().all()

    events = []
    for m in mentions:
        events.append({
            "timestamp": m.created_at.isoformat() if m.created_at else None,
            "event_type": "ENTITY_MENTIONED",
            "entity_type": m.entity_type,
            "raw_text": m.raw_text,
            "confidence": m.confidence,
            "extraction_method": m.extraction_method,
            "evidence_id": str(m.evidence_id),
        })

    events.sort(key=lambda x: x["timestamp"] or "", reverse=True)

    return {
        "entity_id": str(entity_id),
        "events": events,
        "total": len(events),
    }
