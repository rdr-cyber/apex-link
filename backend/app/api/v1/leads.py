"""Lead management routes."""

import uuid
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.repositories.audit_repo import AuditLogRepository
from app.schemas.lead import LeadResponse, LeadListResponse
from app.services.lead_service import LeadService

router = APIRouter(prefix="/leads", tags=["Leads"])


class LeadReviewRequest(BaseModel):
    status: str
    review_notes: str = ""


@router.get("", response_model=LeadListResponse)
async def list_leads(
    case_id: uuid.UUID | None = Query(None),
    priority: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    min_score: float | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List leads with filtering (scoped to accessible cases)."""
    from app.services.case_access_service import get_accessible_case_ids
    service = LeadService(db)
    accessible_ids = await get_accessible_case_ids(db, user)
    if not accessible_ids:
        return LeadListResponse(items=[], total=0, page=page, page_size=page_size)
    # If specific case_id requested, verify access
    if case_id and case_id not in accessible_ids:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Case not found.")
    skip = (page - 1) * page_size
    items, total = await service.lead_repo.search(
        case_id=case_id,
        priority=priority,
        status=status_filter,
        min_score=min_score,
        skip=skip,
        limit=page_size,
        accessible_case_ids=accessible_ids,
    )
    return LeadListResponse(
        items=[LeadResponse.model_validate(l) for l in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{lead_id}")
async def get_lead_detail(
    lead_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detailed lead information with factors and context."""
    from fastapi import HTTPException
    from app.services.case_access_service import can_access_entity, _get_user_case_ids
    from app.models.lead import Lead as LeadModel
    from sqlalchemy import select
    service = LeadService(db)
    # Verify lead exists and user has access
    lead_result = await db.execute(select(LeadModel).where(LeadModel.id == lead_id))
    lead = lead_result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found.")
    accessible = await _get_user_case_ids(db, user)
    if lead.case_id not in accessible:
        raise HTTPException(status_code=404, detail="Lead not found.")
    # Also check related case if present
    if lead.related_case_id and lead.related_case_id not in accessible:
        raise HTTPException(status_code=404, detail="Lead not found.")
    return await service.get_lead_detail(lead_id)


@router.put("/{lead_id}")
async def update_lead(
    lead_id: uuid.UUID,
    body: LeadReviewRequest,
    request: Request,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR", "ANALYST")),
    db: AsyncSession = Depends(get_db),
):
    """Review a lead — update status and add review notes."""
    from fastapi import HTTPException
    from app.services.case_access_service import _get_user_case_ids
    from app.models.lead import Lead as LeadModel
    from sqlalchemy import select
    service = LeadService(db)
    # Verify access
    lead_result = await db.execute(select(LeadModel).where(LeadModel.id == lead_id))
    lead_check = lead_result.scalar_one_or_none()
    if not lead_check:
        raise HTTPException(status_code=404, detail="Lead not found.")
    accessible = await _get_user_case_ids(db, user)
    if lead_check.case_id not in accessible:
        raise HTTPException(status_code=404, detail="Lead not found.")
    lead = await service.review_lead(
        lead_id=lead_id,
        new_status=body.status,
        reviewed_by=user.id,
        review_notes=body.review_notes,
    )

    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="LEAD_REVIEWED",
        resource_type="LEAD",
        resource_id=str(lead_id),
        details=f"Lead status updated to {body.status}",
        ip_address=request.client.host if request and request.client else None,
        case_id=lead.case_id,
    )

    return LeadResponse.model_validate(lead)
