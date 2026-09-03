"""Cross-case correlation routes."""

import uuid
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.repositories.audit_repo import AuditLogRepository
from app.services.lead_service import LeadService

router = APIRouter(prefix="/cases/{case_id}/correlations", tags=["Correlations"])


@router.post("")
async def run_correlation(
    case_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR", "ANALYST")),
    db: AsyncSession = Depends(get_db),
):
    """Run cross-case correlation analysis."""
    service = LeadService(db)
    leads = await service.generate_cross_case_leads(case_id, user.id)

    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="CORRELATION_EXECUTED",
        resource_type="CASE",
        resource_id=str(case_id),
        details=f"Cross-case correlation generated {len(leads)} leads",
        ip_address=request.client.host if request and request.client else None,
        case_id=case_id,
    )

    return {"case_id": str(case_id), "correlations": leads, "total": len(leads)}


@router.get("")
async def get_correlations(
    case_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get existing correlations for a case."""
    service = LeadService(db)
    leads, total = await service.lead_repo.search(case_id=case_id, limit=100)

    return {
        "case_id": str(case_id),
        "correlations": [
            {
                "id": str(l.id),
                "related_case_id": str(l.related_case_id) if l.related_case_id else None,
                "score": l.score,
                "priority": l.priority.value,
                "explanation": l.explanation,
                "status": l.status.value,
            }
            for l in leads
        ],
        "total": total,
    }
