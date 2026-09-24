"""Report generation routes."""

import uuid
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.repositories.audit_repo import AuditLogRepository
from app.services.report_service import ReportService
from app.services.pdf_report_service import PDFReportService
from app.services.case_access_service import require_case_access

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/case/{case_id}")
async def generate_report(
    case_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR", "ANALYST")),
    db: AsyncSession = Depends(get_db),
):
    """Generate an investigation analysis report for a case."""
    await require_case_access(db, user, case_id)
    service = ReportService(db)
    report = await service.generate_case_report(case_id)

    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="REPORT_GENERATED",
        resource_type="CASE",
        resource_id=str(case_id),
        details=f"Report generated for case {case_id}",
        ip_address=request.client.host if request and request.client else None,
        case_id=case_id,
    )

    return JSONResponse(content=report)


@router.post("/case/{case_id}/pdf")
async def generate_pdf_report(
    case_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR", "ANALYST")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a PDF investigation analysis report."""
    await require_case_access(db, user, case_id)
    service = PDFReportService(db)
    pdf_bytes = await service.generate_pdf(case_id)

    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="PDF_REPORT_GENERATED",
        resource_type="CASE",
        resource_id=str(case_id),
        details=f"PDF report generated for case {case_id}",
        ip_address=request.client.host if request and request.client else None,
        case_id=case_id,
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=apex-link-report-{case_id}.pdf"},
    )
