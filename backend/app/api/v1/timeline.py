"""Timeline analysis routes."""

import uuid
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.evidence import Evidence
from app.models.entity import CaseEntity
from app.models.lead import Lead
from app.services.case_access_service import require_case_access

router = APIRouter(prefix="/cases/{case_id}/timeline", tags=["Timeline"])


@router.get("")
async def get_timeline(
    case_id: uuid.UUID,
    entity_id: uuid.UUID | None = Query(None),
    event_type: str | None = Query(None),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get a timeline of events for a case."""
    await require_case_access(db, user, case_id)
    events = []

    # Evidence collection events
    ev_stmt = (
        select(Evidence)
        .where(Evidence.case_id == case_id)
        .order_by(desc(Evidence.collected_at))
    )
    ev_result = await db.execute(ev_stmt)
    for ev in ev_result.scalars().all():
        if ev.collected_at:
            events.append({
                "timestamp": ev.collected_at.isoformat(),
                "event_type": "EVIDENCE_COLLECTED",
                "entity_type": ev.evidence_type.value,
                "description": f"Evidence {ev.evidence_number}: {ev.filename}",
                "evidence_id": str(ev.id),
            })

    # Entity creation events
    ce_stmt = (
        select(CaseEntity)
        .where(CaseEntity.case_id == case_id)
        .order_by(desc(CaseEntity.created_at))
    )
    ce_result = await db.execute(ce_stmt)
    for ce in ce_result.scalars().all():
        events.append({
            "timestamp": ce.created_at.isoformat(),
            "event_type": "ENTITY_LINKED",
            "description": f"Entity linked to case (confidence: {ce.confidence})",
            "entity_id": str(ce.entity_id),
        })

    # Lead events
    lead_stmt = (
        select(Lead)
        .where(Lead.case_id == case_id)
        .order_by(desc(Lead.created_at))
    )
    lead_result = await db.execute(lead_stmt)
    for lead in lead_result.scalars().all():
        events.append({
            "timestamp": lead.created_at.isoformat(),
            "event_type": "LEAD_CREATED",
            "description": f"Lead generated (score: {lead.score}, priority: {lead.priority.value})",
            "lead_id": str(lead.id),
        })

    # Sort by timestamp
    events.sort(key=lambda x: x["timestamp"], reverse=True)

    # Apply filters
    if event_type:
        events = [e for e in events if e["event_type"] == event_type]

    return {"case_id": str(case_id), "events": events, "total": len(events)}
