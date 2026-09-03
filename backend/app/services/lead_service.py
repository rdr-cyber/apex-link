"""Lead generation and scoring service.

Every lead must store score, factors, supporting evidence, and explanation.
Every lead must clearly distinguish facts from algorithmic inferences.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ALGORITHM_VERSION
from app.models.entity import Entity, CaseEntity
from app.models.case import Case
from app.models.relationship import Relationship
from app.models.lead import Lead, LeadPriority, LeadStatus
from app.repositories.lead_repo import LeadRepository


class LeadService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.lead_repo = LeadRepository(db)

    async def generate_cross_case_leads(
        self, case_id: uuid.UUID, executed_by: uuid.UUID
    ) -> list[dict[str, Any]]:
        """Generate cross-case correlation leads using the correlation engine."""
        from app.services.cross_case_correlation import CrossCaseCorrelationService
        correlation_service = CrossCaseCorrelationService(self.db)
        return await correlation_service.correlate_case(case_id, executed_by)

    async def get_lead(self, lead_id: uuid.UUID) -> Lead:
        """Get a single lead by ID."""
        lead = await self.lead_repo.get_by_id(lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="Lead not found.")
        return lead

    async def review_lead(
        self,
        lead_id: uuid.UUID,
        new_status: str,
        reviewed_by: uuid.UUID,
        review_notes: str = "",
    ) -> Lead:
        """Review a lead — update status, notes, and audit."""
        lead = await self.lead_repo.get_by_id(lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="Lead not found.")

        # Validate status transition
        valid_transitions = {
            "NEW": ["REVIEWING"],
            "REVIEWING": ["CONFIRMED", "DISMISSED"],
            "CONFIRMED": [],
            "DISMISSED": ["REVIEWING"],
        }
        current = lead.status.value if hasattr(lead.status, 'value') else lead.status
        if new_status not in valid_transitions.get(current, []):
            raise HTTPException(
                status_code=422,
                detail=f"Cannot transition from {current} to {new_status}."
            )

        lead = await self.lead_repo.update(
            lead,
            status=LeadStatus(new_status),
            reviewed_by=reviewed_by,
            reviewed_at=datetime.now(timezone.utc),
            review_notes=review_notes,
        )
        return lead

    async def get_lead_stats(self, case_id: uuid.UUID | None = None) -> dict:
        """Get lead statistics."""
        leads, total = await self.lead_repo.search(case_id=case_id, limit=10000)
        high_priority = sum(1 for l in leads if l.priority in [LeadPriority.HIGH, LeadPriority.CRITICAL])
        return {
            "total": total,
            "high_priority": high_priority,
            "new": sum(1 for l in leads if l.status == LeadStatus.NEW),
            "reviewing": sum(1 for l in leads if l.status == LeadStatus.REVIEWING),
            "confirmed": sum(1 for l in leads if l.status == LeadStatus.CONFIRMED),
            "dismissed": sum(1 for l in leads if l.status == LeadStatus.DISMISSED),
        }

    async def get_lead_detail(self, lead_id: uuid.UUID) -> dict[str, Any]:
        """Get detailed lead information with factors and context."""
        lead = await self.lead_repo.get_by_id(lead_id)
        if lead is None:
            raise HTTPException(status_code=404, detail="Lead not found.")

        factors = json.loads(lead.factors) if lead.factors else []

        # Get case numbers
        case_number = "Unknown"
        related_case_number = "Unknown"
        if lead.case_id:
            r = await self.db.execute(select(Case.case_number).where(Case.id == lead.case_id))
            case_number = r.scalar_one_or_none() or "Unknown"
        if lead.related_case_id:
            r = await self.db.execute(select(Case.case_number).where(Case.id == lead.related_case_id))
            related_case_number = r.scalar_one_or_none() or "Unknown"

        return {
            "id": str(lead.id),
            "case_id": str(lead.case_id),
            "case_number": case_number,
            "related_case_id": str(lead.related_case_id) if lead.related_case_id else None,
            "related_case_number": related_case_number,
            "lead_type": lead.lead_type,
            "score": lead.score,
            "priority": lead.priority.value if hasattr(lead.priority, 'value') else lead.priority,
            "explanation": lead.explanation,
            "factors": factors,
            "status": lead.status.value if hasattr(lead.status, 'value') else lead.status,
            "review_notes": lead.review_notes,
            "created_at": lead.created_at.isoformat() if lead.created_at else None,
            "reviewed_by": str(lead.reviewed_by) if lead.reviewed_by else None,
            "reviewed_at": lead.reviewed_at.isoformat() if lead.reviewed_at else None,
            "algorithm_version": ALGORITHM_VERSION,
        }
