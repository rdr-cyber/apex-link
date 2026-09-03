"""Evidence routes — upload, list, verify integrity."""

import uuid
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.repositories.audit_repo import AuditLogRepository
from app.repositories.evidence_repo import EvidenceRepository
from app.schemas.evidence import EvidenceResponse, EvidenceListResponse, IntegrityResponse
from app.models.evidence import EvidenceType
from app.services.evidence_service import EvidenceService
from app.services.case_access_service import require_case_access

router = APIRouter(prefix="/cases/{case_id}/evidence", tags=["Evidence"])


@router.post("", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
async def upload_evidence(
    case_id: uuid.UUID,
    file: UploadFile = File(...),
    evidence_type: str = Form("DOCUMENT"),
    description: str = Form(""),
    source: str = Form("unknown"),
    collected_by: str | None = Form(None),
    request: Request = None,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR")),
    db: AsyncSession = Depends(get_db),
):
    """Upload evidence to a case."""
    await require_case_access(db, user, case_id)
    # Validate evidence_type enum
    try:
        ev_type = EvidenceType(evidence_type)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid evidence type '{evidence_type}'. "
                   f"Valid types: {', '.join(t.value for t in EvidenceType)}",
        )

    service = EvidenceService(db)
    result = await service.upload_evidence(
        case_id=case_id,
        file=file,
        evidence_type=ev_type,
        description=description,
        source=source,
        collected_by=collected_by,
    )

    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="EVIDENCE_UPLOADED",
        resource_type="EVIDENCE",
        resource_id=str(result.id),
        details=f"Evidence {result.evidence_number} uploaded: {result.filename}",
        ip_address=request.client.host if request and request.client else None,
        case_id=case_id,
    )

    return result


@router.get("", response_model=EvidenceListResponse)
async def list_evidence(
    case_id: uuid.UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List evidence for a case."""
    await require_case_access(db, user, case_id)
    repo = EvidenceRepository(db)
    skip = (page - 1) * page_size
    items, total = await repo.get_by_case(case_id, skip=skip, limit=page_size)
    return EvidenceListResponse(
        items=[EvidenceResponse.model_validate(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{evidence_id}/integrity", response_model=IntegrityResponse)
async def verify_integrity(
    case_id: uuid.UUID,
    evidence_id: uuid.UUID,
    request: Request,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Verify evidence integrity using SHA-256 hash."""
    service = EvidenceService(db)
    result = await service.verify_integrity(evidence_id)

    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="EVIDENCE_INTEGRITY_CHECK",
        resource_type="EVIDENCE",
        resource_id=str(evidence_id),
        details=f"Integrity check: {result['integrity_status']}",
        ip_address=request.client.host if request and request.client else None,
        case_id=case_id,
    )

    return IntegrityResponse(**result)
