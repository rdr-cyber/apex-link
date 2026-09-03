"""Global search routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.case import Case
from app.models.entity import Entity
from app.models.evidence import Evidence

router = APIRouter(prefix="/search", tags=["Search"])


@router.get("")
async def global_search(
    q: str = Query(..., min_length=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Search across cases, entities, and evidence (user-scoped)."""
    from app.services.case_access_service import get_accessible_case_ids
    from app.models.entity import CaseEntity
    from app.models.evidence import Evidence as EvidenceModel

    results = []
    limit = 20

    # Get accessible case IDs for this user
    accessible_ids = await get_accessible_case_ids(db, user)
    if not accessible_ids:
        return {"results": [], "total": 0}

    # Search cases (scoped)
    case_stmt = (
        select(Case)
        .where(
            Case.id.in_(accessible_ids),
            or_(
                Case.case_number.ilike(f"%{q}%"),
                Case.title.ilike(f"%{q}%"),
                Case.description.ilike(f"%{q}%"),
            )
        )
        .limit(limit)
    )
    case_result = await db.execute(case_stmt)
    for case in case_result.scalars().all():
        results.append({
            "type": "CASE",
            "id": str(case.id),
            "label": case.case_number,
            "subtitle": case.title,
            "detail": case.category,
        })

    # Search entities (scoped to accessible cases)
    ent_stmt = (
        select(Entity)
        .join(CaseEntity, CaseEntity.entity_id == Entity.id)
        .where(
            CaseEntity.case_id.in_(accessible_ids),
            or_(
                Entity.canonical_value.ilike(f"%{q}%"),
                Entity.normalized_value.ilike(f"%{q}%"),
                Entity.display_value.ilike(f"%{q}%"),
            )
        )
        .distinct()
        .limit(limit)
    )
    ent_result = await db.execute(ent_stmt)
    for entity in ent_result.scalars().all():
        results.append({
            "type": entity.entity_type,
            "id": str(entity.id),
            "label": entity.display_value,
            "subtitle": entity.entity_type,
            "detail": f"Confidence: {entity.confidence}",
        })

    # Search evidence (scoped to accessible cases)
    ev_stmt = (
        select(Evidence)
        .where(
            Evidence.case_id.in_(accessible_ids),
            or_(
                Evidence.evidence_number.ilike(f"%{q}%"),
                Evidence.filename.ilike(f"%{q}%"),
                Evidence.description.ilike(f"%{q}%"),
            )
        )
        .limit(limit)
    )
    ev_result = await db.execute(ev_stmt)
    for ev in ev_result.scalars().all():
        results.append({
            "type": "EVIDENCE",
            "id": str(ev.id),
            "label": ev.evidence_number,
            "subtitle": ev.filename,
            "detail": ev.evidence_type.value,
        })

    return {"results": results, "total": len(results)}
