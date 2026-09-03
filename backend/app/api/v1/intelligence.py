"""High-Impact Intelligence routes — Path Finder, Explain Connection, Cross-Case Timeline."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.user import User
from app.repositories.audit_repo import AuditLogRepository
from app.services.case_access_service import get_accessible_case_ids, require_case_access

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])


# ──────────────────────────────────────────────
# Network Path Finder
# ──────────────────────────────────────────────

@router.post("/path", response_model=dict)
async def find_network_path(
    body: dict,
    request: Request,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR", "ANALYST")),
    db: AsyncSession = Depends(get_db),
):
    """Find an evidence-backed network path between two cases or entities."""
    source_type = body.get("source_type", "CASE")
    target_type = body.get("target_type", "CASE")

    if source_type not in ("CASE", "ENTITY") or target_type not in ("CASE", "ENTITY"):
        raise HTTPException(status_code=400, detail="source_type and target_type must be CASE or ENTITY.")

    try:
        source_id = uuid.UUID(body["source_id"])
        target_id = uuid.UUID(body["target_id"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="source_id and target_id must be valid UUIDs.")

    # Authorization
    accessible = await get_accessible_case_ids(db, user)
    if source_type == "CASE":
        await require_case_access(db, user, source_id)
    if target_type == "CASE":
        await require_case_access(db, user, target_id)

    from app.services.path_finder import PathFinderService
    service = PathFinderService(db)
    result = await service.find_path(
        source_id=source_id,
        source_type=source_type,
        target_id=target_id,
        target_type=target_type,
        accessible_case_ids=accessible,
    )

    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="PATH_FINDER_EXECUTED",
        resource_type="ANALYSIS",
        resource_id=str(source_id),
        details=f"Path finding: {source_type} -> {target_type}, found={result.get('path_found', False)}",
        ip_address=request.client.host if request and request.client else None,
    )

    return result


@router.get("/cases-for-path", response_model=list[dict])
async def list_cases_for_path(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List cases available for path-finder selection."""
    accessible = await get_accessible_case_ids(db, user)
    from app.services.path_finder import PathFinderService
    service = PathFinderService(db)
    return await service.list_cases_for_selection(accessible)


# ──────────────────────────────────────────────
# Explain Connection
# ──────────────────────────────────────────────

@router.post("/explain-connection", response_model=dict)
async def explain_connection(
    body: dict,
    request: Request,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR", "ANALYST")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a structured explanation for why two cases are connected."""
    try:
        case_id = uuid.UUID(body["case_id"])
        related_case_id = uuid.UUID(body["related_case_id"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=400, detail="case_id and related_case_id must be valid UUIDs.")

    # Authorization
    await require_case_access(db, user, case_id)
    await require_case_access(db, user, related_case_id)

    from app.services.connection_explainer import ConnectionExplainerService
    service = ConnectionExplainerService(db)
    result = await service.explain_connection(case_id, related_case_id)

    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="CONNECTION_EXPLAINED",
        resource_type="CASE",
        resource_id=str(case_id),
        details=f"Explained connection to {related_case_id}",
        ip_address=request.client.host if request and request.client else None,
        case_id=case_id,
    )

    return result


# ──────────────────────────────────────────────
# Cross-Case Timeline
# ──────────────────────────────────────────────

@router.post("/cross-case-timeline", response_model=dict)
async def get_cross_case_timeline(
    body: dict,
    request: Request,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR", "ANALYST")),
    db: AsyncSession = Depends(get_db),
):
    """Get a merged timeline from multiple authorized cases."""
    case_ids_raw = body.get("case_ids", [])
    if len(case_ids_raw) < 2:
        raise HTTPException(status_code=400, detail="At least 2 case IDs required.")
    if len(case_ids_raw) > 5:
        raise HTTPException(status_code=400, detail="Maximum 5 cases for timeline comparison.")

    case_ids = [uuid.UUID(cid) for cid in case_ids_raw]
    accessible = await get_accessible_case_ids(db, user)

    # Verify access to all cases
    for cid in case_ids:
        await require_case_access(db, user, cid)

    from app.services.cross_case_timeline import CrossCaseTimelineService
    service = CrossCaseTimelineService(db)
    result = await service.get_cross_case_timeline(
        case_ids=case_ids,
        accessible_case_ids=accessible,
        event_type=body.get("event_type"),
        entity_type=body.get("entity_type"),
        date_from=body.get("date_from"),
        date_to=body.get("date_to"),
    )

    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="CROSS_CASE_TIMELINE",
        resource_type="ANALYSIS",
        resource_id=str(case_ids[0]),
        details=f"Cross-case timeline for {len(case_ids)} cases, {result.get('total', 0)} events",
        ip_address=request.client.host if request and request.client else None,
    )

    return result
