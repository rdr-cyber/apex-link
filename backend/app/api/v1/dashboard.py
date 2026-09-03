"""Dashboard statistics routes."""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.case import Case, CaseStatus, CasePriority
from app.models.evidence import Evidence
from app.models.entity import Entity
from app.models.relationship import Relationship
from app.models.lead import Lead, LeadPriority
from app.repositories.case_repo import CaseRepository
from app.repositories.evidence_repo import EvidenceRepository
from app.repositories.entity_repo import EntityRepository
from app.repositories.relationship_repo import RelationshipRepository
from app.repositories.lead_repo import LeadRepository

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("")
async def get_dashboard_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get dashboard statistics (scoped to user's accessible cases)."""
    from app.services.case_access_service import get_accessible_case_ids
    from app.models.entity import CaseEntity
    from app.models.evidence import Evidence as EvidenceModel

    accessible_ids = await get_accessible_case_ids(db, user)
    if not accessible_ids:
        return {
            "total_cases": 0, "active_cases": 0, "total_evidence": 0,
            "total_entities": 0, "total_relationships": 0, "high_priority_leads": 0,
            "cases_by_status": {}, "cases_by_priority": {}, "cases_by_category": {},
            "lead_priority_distribution": {}, "entity_type_distribution": {},
        }

    # Cases by status (scoped)
    status_counts = {}
    for s in CaseStatus:
        result = await db.execute(select(func.count(Case.id)).where(
            Case.id.in_(accessible_ids), Case.status == s))
        status_counts[s.value] = result.scalar_one()
    total_cases = sum(status_counts.values())
    active_cases = sum(status_counts.get(s.value, 0) for s in [CaseStatus.OPEN, CaseStatus.UNDER_REVIEW, CaseStatus.ANALYSIS])

    # Cases by priority (scoped)
    priority_counts = {}
    for p in CasePriority:
        result = await db.execute(select(func.count(Case.id)).where(
            Case.id.in_(accessible_ids), Case.priority == p))
        priority_counts[p.value] = result.scalar_one()

    # Cases by category (scoped)
    cat_stmt = select(Case.category, func.count(Case.id)).where(
        Case.id.in_(accessible_ids)).group_by(Case.category)
    cat_result = await db.execute(cat_stmt)
    category_counts = {row[0]: row[1] for row in cat_result.all()}

    # Evidence count (scoped)
    ev_result = await db.execute(select(func.count(EvidenceModel.id)).where(
        EvidenceModel.case_id.in_(accessible_ids)))
    total_evidence = ev_result.scalar_one()

    # Entity count (scoped via CaseEntity)
    ent_result = await db.execute(select(func.count(CaseEntity.entity_id.distinct())).where(
        CaseEntity.case_id.in_(accessible_ids)))
    total_entities = ent_result.scalar_one()

    # Relationship count (scoped)
    from app.models.relationship import Relationship
    rel_result = await db.execute(select(func.count(Relationship.id)).where(
        Relationship.case_id.in_(accessible_ids)))
    total_relationships = rel_result.scalar_one()

    # Lead count (scoped)
    from app.models.lead import Lead as LeadModel
    lead_result = await db.execute(select(func.count(LeadModel.id)).where(
        LeadModel.case_id.in_(accessible_ids)))
    high_priority_leads = lead_result.scalar_one()

    # Lead priority distribution (scoped)
    lead_priority_counts = {}
    for p in LeadPriority:
        result = await db.execute(select(func.count(LeadModel.id)).where(
            LeadModel.case_id.in_(accessible_ids), LeadModel.priority == p))
        lead_priority_counts[p.value] = result.scalar_one()

    # Entity type distribution (scoped)
    from app.models.entity import EntityType
    entity_type_counts = {}
    for t in EntityType:
        result = await db.execute(select(func.count(CaseEntity.entity_id.distinct())).where(
            CaseEntity.case_id.in_(accessible_ids),
            CaseEntity.entity_id.in_(
                select(Entity.id).where(Entity.entity_type == t)
            )
        ))
        count = result.scalar_one()
        if count > 0:
            entity_type_counts[t.value] = count

    return {
        "total_cases": total_cases,
        "active_cases": active_cases,
        "total_evidence": total_evidence,
        "total_entities": total_entities,
        "total_relationships": total_relationships,
        "high_priority_leads": high_priority_leads,
        "cases_by_status": status_counts,
        "cases_by_priority": priority_counts,
        "cases_by_category": category_counts,
        "lead_priority_distribution": lead_priority_counts,
        "entity_type_distribution": entity_type_counts,
    }
