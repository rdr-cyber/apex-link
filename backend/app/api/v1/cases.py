"""Case management routes."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.repositories.audit_repo import AuditLogRepository
from app.schemas.case import CaseCreate, CaseUpdate, CaseResponse, CaseListResponse
from app.services.case_service import CaseService
from app.services.case_access_service import require_case_access, require_case_edit
from app.repositories.case_repo import CaseRepository

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
async def create_case(
    body: CaseCreate,
    request: Request,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR")),
    db: AsyncSession = Depends(get_db),
):
    """Create a new investigation case."""
    service = CaseService(db)
    result = await service.create_case(body, user.id)

    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="CASE_CREATED",
        resource_type="CASE",
        resource_id=str(result.id),
        details=f"Case {result.case_number} created",
        ip_address=request.client.host if request.client else None,
    )

    return result


@router.get("", response_model=CaseListResponse)
async def list_cases(
    query: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    priority: str | None = Query(None),
    category: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List cases with filtering and pagination."""
    from app.services.case_access_service import get_accessible_case_ids
    service = CaseService(db)
    accessible_ids = await get_accessible_case_ids(db, user)
    return await service.list_cases(
        query=query,
        case_status=status_filter,
        priority=priority,
        category=category,
        page=page,
        page_size=page_size,
        accessible_case_ids=accessible_ids,
    )


@router.get("/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a case by ID."""
    await require_case_access(db, user, case_id)
    service = CaseService(db)
    return await service.get_case(case_id)


@router.put("/{case_id}", response_model=CaseResponse)
async def update_case(
    case_id: uuid.UUID,
    body: CaseUpdate,
    request: Request,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR")),
    db: AsyncSession = Depends(get_db),
):
    """Update a case."""
    await require_case_access(db, user, case_id)
    repo = CaseRepository(db)
    case = await repo.get_by_id(case_id)
    if case:
        await require_case_edit(db, user, case)
    service = CaseService(db)
    result = await service.update_case(case_id, body)

    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="CASE_UPDATED",
        resource_type="CASE",
        resource_id=str(case_id),
        details=f"Case {result.case_number} updated",
        ip_address=request.client.host if request.client else None,
        case_id=case_id,
    )

    return result


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case(
    case_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """Delete a case (admin only)."""
    service = CaseService(db)
    await service.delete_case(case_id)

    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="CASE_DELETED",
        resource_type="CASE",
        resource_id=str(case_id),
        details="Case deleted",
        ip_address=request.client.host if request.client else None,
    )
