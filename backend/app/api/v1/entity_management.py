"""Entity management routes — correction, merge, mention ignore."""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.models.entity import Entity, CaseEntity
from app.models.entity_mention import EntityMention
from app.models.relationship import Relationship
from app.repositories.audit_repo import AuditLogRepository
from app.repositories.entity_repo import EntityRepository
from app.services.case_access_service import require_entity_access

router = APIRouter(prefix="/entities", tags=["Entity Management"])


class EntityCorrectionRequest(BaseModel):
    display_value: str | None = Field(None, min_length=1, max_length=1000)
    normalized_value: str | None = Field(None, min_length=1, max_length=1000)
    reason: str = Field(..., min_length=1, max_length=500)


class EntityMergeRequest(BaseModel):
    target_entity_id: uuid.UUID
    reason: str = Field(..., min_length=1, max_length=500)


class MentionIgnoreRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=500)


@router.put("/{entity_id}/correct")
async def correct_entity(
    entity_id: uuid.UUID,
    body: EntityCorrectionRequest,
    request: Request,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR")),
    db: AsyncSession = Depends(get_db),
):
    """Correct an entity's display or normalized value. Original evidence is never modified."""
    await require_entity_access(db, user, entity_id)
    repo = EntityRepository(db)
    entity = await repo.get_by_id(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found.")

    before_display = entity.display_value
    before_normalized = entity.normalized_value

    updates = {}
    if body.display_value is not None:
        updates["display_value"] = body.display_value
    if body.normalized_value is not None:
        updates["normalized_value"] = body.normalized_value

    if not updates:
        raise HTTPException(status_code=422, detail="No corrections provided.")

    entity = await repo.update(entity, **updates)

    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="ENTITY_CORRECTED",
        resource_type="ENTITY",
        resource_id=str(entity_id),
        details=f"Before: display='{before_display}', normalized='{before_normalized}'. "
                f"After: display='{entity.display_value}', normalized='{entity.normalized_value}'. "
                f"Reason: {body.reason}",
        ip_address=request.client.host if request and request.client else None,
    )

    return {
        "id": str(entity.id),
        "entity_type": entity.entity_type.value,
        "display_value": entity.display_value,
        "normalized_value": entity.normalized_value,
        "corrected_by": str(user.id),
        "corrected_at": datetime.now(timezone.utc).isoformat(),
        "message": "Entity corrected. Original evidence is unmodified.",
    }


@router.post("/{entity_id}/merge")
async def merge_entities(
    entity_id: uuid.UUID,
    body: EntityMergeRequest,
    request: Request,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR")),
    db: AsyncSession = Depends(get_db),
):
    """Merge source entity into target entity. Preserves provenance."""
    await require_entity_access(db, user, entity_id)
    await require_entity_access(db, user, body.target_entity_id)
    repo = EntityRepository(db)
    source = await repo.get_by_id(entity_id)
    target = await repo.get_by_id(body.target_entity_id)

    if source is None:
        raise HTTPException(status_code=404, detail="Source entity not found.")
    if target is None:
        raise HTTPException(status_code=404, detail="Target entity not found.")
    if source.id == target.id:
        raise HTTPException(status_code=422, detail="Cannot merge an entity with itself.")

    # Type compatibility check
    _pairs = [
        ("PHONE", "EMAIL"), ("PHONE", "IP_ADDRESS"), ("PHONE", "UPI_ID"),
        ("EMAIL", "IP_ADDRESS"), ("EMAIL", "UPI_ID"), ("IP_ADDRESS", "UPI_ID"),
    ]
    incompatible_pairs = {frozenset(p) for p in _pairs}
    def _etype(entity):
        et = entity.entity_type
        if hasattr(et, 'value'):
            return et.value
        return str(et).split('.')[-1].strip("'\"").upper()

    src_type = _etype(source)
    tgt_type = _etype(target)
    type_pair = frozenset([src_type, tgt_type])
    if type_pair in incompatible_pairs:
        raise HTTPException(
            status_code=422,
            detail=f"Cannot merge {src_type} with {tgt_type}. "
                   f"Incompatible entity types.",
        )

    # Count affected records
    source_ce_stmt = select(CaseEntity).where(CaseEntity.entity_id == source.id)
    source_ce_result = await db.execute(source_ce_stmt)
    source_ces = source_ce_result.scalars().all()

    source_rel_stmt = select(Relationship).where(
        (Relationship.source_entity_id == source.id) | (Relationship.target_entity_id == source.id)
    )
    source_rel_result = await db.execute(source_rel_stmt)
    source_rels = source_rel_result.scalars().all()

    # Re-point case entities
    for ce in source_ces:
        # Check if target already has a CaseEntity for this case
        existing_stmt = select(CaseEntity).where(
            CaseEntity.case_id == ce.case_id,
            CaseEntity.entity_id == target.id,
        )
        existing_result = await db.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()

        if existing is None:
            ce.entity_id = target.id
        else:
            # Target already linked — remove source link
            await db.delete(ce)

    # Re-point relationships
    for rel in source_rels:
        if rel.source_entity_id == source.id:
            rel.source_entity_id = target.id
        if rel.target_entity_id == source.id:
            rel.target_entity_id = target.id

    # Update entity mentions to point to target
    mention_stmt = select(EntityMention).where(EntityMention.normalized_value == source.normalized_value)
    mention_result = await db.execute(mention_stmt)
    mentions = mention_result.scalars().all()
    for m in mentions:
        m.normalized_value = target.normalized_value

    # Mark source as merged (soft-delete by appending to display value)
    await repo.update(
        source,
        display_value=f"[MERGED into {target.id}] {source.display_value}",
        normalized_value=f"merged_{source.id}",
    )

    await db.flush()

    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="ENTITY_MERGED",
        resource_type="ENTITY",
        resource_id=str(entity_id),
        details=f"Entity {source.display_value} ({source.entity_type.value}) merged into "
                f"{target.display_value} ({target.entity_type.value}). "
                f"{len(source_ces)} case links, {len(source_rels)} relationships re-pointed. "
                f"Reason: {body.reason}",
        ip_address=request.client.host if request and request.client else None,
    )

    return {
        "source_entity_id": str(source.id),
        "target_entity_id": str(target.id),
        "target_display_value": target.display_value,
        "case_links_repointed": len(source_ces),
        "relationships_repointed": len(source_rels),
        "mentions_repointed": len(mentions),
        "merged_by": str(user.id),
        "merged_at": datetime.now(timezone.utc).isoformat(),
        "message": "Entity merged. Original evidence references are preserved.",
    }


@router.get("/{entity_id}/merge-preview")
async def merge_preview(
    entity_id: uuid.UUID,
    target_id: uuid.UUID,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR")),
    db: AsyncSession = Depends(get_db),
):
    """Preview consequences of merging two entities."""
    repo = EntityRepository(db)
    source = await repo.get_by_id(entity_id)
    target = await repo.get_by_id(target_id)

    if source is None or target is None:
        raise HTTPException(status_code=404, detail="Entity not found.")

    # Count records for source
    source_ce_stmt = select(CaseEntity).where(CaseEntity.entity_id == source.id)
    source_ce_result = await db.execute(source_ce_stmt)
    source_ces = source_ce_result.scalars().all()

    target_ce_stmt = select(CaseEntity).where(CaseEntity.entity_id == target.id)
    target_ce_result = await db.execute(target_ce_stmt)
    target_ces = target_ce_result.scalars().all()

    source_rel_stmt = select(Relationship).where(
        (Relationship.source_entity_id == source.id) | (Relationship.target_entity_id == source.id)
    )
    source_rel_result = await db.execute(source_rel_stmt)
    source_rels = source_rel_result.scalars().all()

    # Count overlapping cases
    source_case_ids = {ce.case_id for ce in source_ces}
    target_case_ids = {ce.case_id for ce in target_ces}
    overlapping_cases = source_case_ids & target_case_ids

    return {
        "source": {
            "id": str(source.id),
            "type": source.entity_type.value,
            "display_value": source.display_value,
            "case_count": len(source_ces),
            "relationship_count": len(source_rels),
        },
        "target": {
            "id": str(target.id),
            "type": target.entity_type.value,
            "display_value": target.display_value,
            "case_count": len(target_ces),
        },
        "consequences": {
            "case_links_repointed": len(source_ces) - len(overlapping_cases),
            "case_links_dropped": len(overlapping_cases),
            "relationships_repointed": len(source_rels),
            "total_cases_after": len(target_case_ids | source_case_ids),
        },
    }


@router.put("/mentions/{mention_id}/ignore")
async def ignore_mention(
    mention_id: uuid.UUID,
    body: MentionIgnoreRequest,
    request: Request,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR")),
    db: AsyncSession = Depends(get_db),
):
    """Mark an entity mention as ignored (extraction error). Original evidence is not modified."""
    stmt = select(EntityMention).where(EntityMention.id == mention_id)
    result = await db.execute(stmt)
    mention = result.scalar_one_or_none()
    if mention is None:
        raise HTTPException(status_code=404, detail="Entity mention not found.")

    # Remove any case-entity links created from this mention
    ce_stmt = select(CaseEntity).where(
        CaseEntity.source_evidence_id == mention.evidence_id,
        CaseEntity.mention_text == mention.raw_text,
    )
    ce_result = await db.execute(ce_stmt)
    linked = ce_result.scalars().all()
    for ce in linked:
        await db.delete(ce)

    # Delete the mention itself
    await db.delete(mention)
    await db.flush()

    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="ENTITY_MENTION_IGNORED",
        resource_type="ENTITY_MENTION",
        resource_id=str(mention_id),
        details=f"Mention '{mention.raw_text}' ({mention.entity_type}) ignored. "
                f"{len(linked)} case-entity links removed. Reason: {body.reason}",
        ip_address=request.client.host if request and request.client else None,
    )

    return {
        "mention_id": str(mention_id),
        "ignored_by": str(user.id),
        "ignored_at": datetime.now(timezone.utc).isoformat(),
        "links_removed": len(linked),
        "message": "Mention ignored. Original evidence is unmodified.",
    }
