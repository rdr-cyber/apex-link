"""Audit trail routes."""

import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_role
from app.db.session import get_db
from app.models.user import User
from app.repositories.audit_repo import AuditLogRepository

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("")
async def list_audit_logs(
    user_id: uuid.UUID | None = Query(None),
    action: str | None = Query(None),
    resource_type: str | None = Query(None),
    case_id: uuid.UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    admin: User = Depends(require_role("ADMIN")),
    db: AsyncSession = Depends(get_db),
):
    """List audit logs (admin only)."""
    repo = AuditLogRepository(db)
    skip = (page - 1) * page_size
    items, total = await repo.search(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        case_id=case_id,
        skip=skip,
        limit=page_size,
    )

    return {
        "items": [
            {
                "id": str(log.id),
                "user_id": str(log.user_id),
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "details": log.details,
                "ip_address": log.ip_address,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            }
            for log in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
