"""Analysis routes — entity extraction, full analysis, key entities, patterns, correlation, history."""

import uuid
import hashlib
import os
from pathlib import Path
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, require_role
from app.core.settings import get_settings
from app.db.session import get_db
from app.models.analysis_result import AnalysisResult
from app.models.evidence import Evidence, EvidenceType
from app.models.user import User
from app.repositories.audit_repo import AuditLogRepository
from app.repositories.evidence_repo import EvidenceRepository
from app.services.analysis_service import AnalysisService
from app.services.cross_case_correlation import CrossCaseCorrelationService
from app.services.graph_service import GraphService
from app.services.pattern_detection import PatternDetectionService
from app.services.case_access_service import require_case_access

router = APIRouter(prefix="/cases/{case_id}/analysis", tags=["Analysis"])


@router.post("/run", response_model=dict)
async def run_analysis(
    case_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR", "ANALYST")),
    db: AsyncSession = Depends(get_db),
):
    """Run the full analysis pipeline for a case."""
    await require_case_access(db, user, case_id)
    service = AnalysisService(db)
    result = await service.run_full_analysis(case_id, user.id)

    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="ANALYSIS_EXECUTED",
        resource_type="CASE",
        resource_id=str(case_id),
        details=f"Full analysis executed. Leads: {len(result.get('leads', []))}, Patterns: {len(result.get('suspicious_patterns', []))}",
        ip_address=request.client.host if request and request.client else None,
        case_id=case_id,
    )

    return result


@router.post("/correlate", response_model=dict)
async def run_correlation(
    case_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR", "ANALYST")),
    db: AsyncSession = Depends(get_db),
):
    """Run cross-case correlation analysis."""
    await require_case_access(db, user, case_id)
    from app.services.case_access_service import get_accessible_case_ids
    accessible = await get_accessible_case_ids(db, user)
    service = CrossCaseCorrelationService(db)
    leads = await service.correlate_case(case_id, user.id, accessible_case_ids=accessible)

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

    return {"case_id": str(case_id), "leads_generated": len(leads), "leads": leads}


@router.post("/patterns", response_model=dict)
async def run_pattern_detection(
    case_id: uuid.UUID,
    request: Request,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR", "ANALYST")),
    db: AsyncSession = Depends(get_db),
):
    """Run pattern detection for a case."""
    await require_case_access(db, user, case_id)
    service = PatternDetectionService(db)
    patterns = await service.detect_all_patterns(case_id)

    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="PATTERN_DETECTION_EXECUTED",
        resource_type="CASE",
        resource_id=str(case_id),
        details=f"Pattern detection found {len(patterns)} patterns",
        ip_address=request.client.host if request and request.client else None,
        case_id=case_id,
    )

    return {"case_id": str(case_id), "patterns": patterns, "total": len(patterns)}


@router.post("/ingest/text", response_model=dict)
async def ingest_text(
    case_id: uuid.UUID,
    text: str = Form(...),
    description: str = Form(""),
    request: Request = None,
    user: User = Depends(require_role("ADMIN", "INVESTIGATOR")),
    db: AsyncSession = Depends(get_db),
):
    """Ingest raw text, extract entities, and create relationships."""
    await require_case_access(db, user, case_id)
    settings = get_settings()
    ev_repo = EvidenceRepository(db)

    # Count existing evidence
    ev_count_result = await db.execute(select(func.count(Evidence.id)))
    ev_count = ev_count_result.scalar_one()

    # Save text as evidence
    storage_dir = Path(settings.LOCAL_STORAGE_PATH) / str(case_id) / "text"
    storage_dir.mkdir(parents=True, exist_ok=True)

    safe_name = hashlib.md5(f"{uuid.uuid4()}_text".encode()).hexdigest() + ".txt"
    storage_path = str(storage_dir / safe_name)

    with open(storage_path, "w") as f:
        f.write(text)

    sha256 = hashlib.sha256(text.encode()).hexdigest()

    evidence = await ev_repo.create(
        case_id=case_id,
        evidence_number=f"EV-{ev_count + 1:05d}",
        evidence_type=EvidenceType.SURVEILLANCE_NOTE,
        filename="ingested_text.txt",
        mime_type="text/plain",
        size_bytes=len(text.encode()),
        storage_path=storage_path,
        sha256_hash=sha256,
        description=description or "Ingested text",
        source="text_ingest",
        collected_by=user.full_name,
    )

    # Extract entities
    analysis_service = AnalysisService(db)
    extraction_result = await analysis_service.extract_entities_from_evidence(evidence.id, case_id)

    # Generate relationships
    rel_count = await analysis_service.generate_relationships(case_id)

    audit = AuditLogRepository(db)
    await audit.log(
        user_id=user.id,
        action="TEXT_INGESTED",
        resource_type="CASE",
        resource_id=str(case_id),
        details=f"Text ingested, {extraction_result['total_extracted']} entities extracted",
        ip_address=request.client.host if request and request.client else None,
        case_id=case_id,
    )

    return {
        "evidence_id": str(evidence.id),
        "extraction": extraction_result,
        "relationships_generated": rel_count,
    }


@router.get("/key-entities", response_model=list[dict])
async def get_key_entities(
    case_id: uuid.UUID,
    top_n: int = 10,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get key/highly-connected entities for a case."""
    await require_case_access(db, user, case_id)
    service = GraphService(db)
    return await service.get_key_entities(case_id, top_n)


@router.get("/patterns", response_model=list[dict])
async def get_patterns(
    case_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get detected patterns for a case."""
    await require_case_access(db, user, case_id)
    service = PatternDetectionService(db)
    return await service.detect_all_patterns(case_id)


@router.get("/correlations", response_model=dict)
async def get_correlations(
    case_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get existing correlation leads for a case."""
    await require_case_access(db, user, case_id)
    service = CrossCaseCorrelationService(db)
    correlations = await service.get_correlations_for_case(case_id)
    return {"case_id": str(case_id), "correlations": correlations, "total": len(correlations)}


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
    source_id = uuid.UUID(body["source_id"])
    target_type = body.get("target_type", "CASE")
    target_id = uuid.UUID(body["target_id"])

    if source_type not in ("CASE", "ENTITY") or target_type not in ("CASE", "ENTITY"):
        raise HTTPException(status_code=400, detail="source_type and target_type must be CASE or ENTITY.")

    # Authorization: verify user can access both source and target cases
    from app.services.case_access_service import get_accessible_case_ids, require_case_access
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
    from app.services.case_access_service import get_accessible_case_ids
    from app.services.path_finder import PathFinderService
    accessible = await get_accessible_case_ids(db, user)
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
    case_id = uuid.UUID(body["case_id"])
    related_case_id = uuid.UUID(body["related_case_id"])

    # Authorization
    from app.services.case_access_service import require_case_access
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

    from app.services.case_access_service import get_accessible_case_ids
    accessible = await get_accessible_case_ids(db, user)

    event_type = body.get("event_type")
    entity_type = body.get("entity_type")
    date_from = body.get("date_from")
    date_to = body.get("date_to")

    from app.services.cross_case_timeline import CrossCaseTimelineService
    service = CrossCaseTimelineService(db)
    result = await service.get_cross_case_timeline(
        case_ids=case_ids,
        accessible_case_ids=accessible,
        event_type=event_type,
        entity_type=entity_type,
        date_from=date_from,
        date_to=date_to,
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
