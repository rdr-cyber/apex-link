"""Cross-case correlation engine.

Compares a case against other cases and produces explainable correlation leads.
Uses indexed entity overlap to avoid all-pairs comparisons.
"""

import json
import uuid
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ALGORITHM_VERSION, CROSS_CASE_WEIGHTS
from app.models.entity import Entity, CaseEntity
from app.models.case import Case
from app.models.lead import Lead, LeadPriority, LeadStatus


def _score_to_priority(score: float) -> LeadPriority:
    """Map correlation score to lead priority."""
    if score >= 75:
        return LeadPriority.CRITICAL
    elif score >= 50:
        return LeadPriority.HIGH
    elif score >= 25:
        return LeadPriority.MEDIUM
    return LeadPriority.LOW


def _compute_correlation_score(
    shared_entities: list[dict],
    max_possible: int,
) -> tuple[float, list[dict], list[str]]:
    """Compute explainable correlation score from shared entities.

    Returns (normalized_score, factors, reason_texts).
    """
    factors = []
    total_weight = 0
    seen_types: set[str] = set()  # Prevent double-counting same entity type

    for ent in shared_entities:
        etype = ent["entity_type"]
        # Deduplicate: only count the highest-weight match per type
        weight_key = {
            "PHONE": "phone_exact",
            "UPI_ID": "upi_exact",
            "EMAIL": "email_exact",
            "IP_ADDRESS": "ip_exact",
            "DEVICE": "device_exact",
            "VEHICLE": "vehicle_exact",
            "ORGANIZATION": "organization_exact",
            "LOCATION": "location_proximity",
        }.get(etype)

        if weight_key and weight_key not in seen_types and weight_key in CROSS_CASE_WEIGHTS:
            seen_types.add(weight_key)
            weight = CROSS_CASE_WEIGHTS[weight_key]
            total_weight += weight
            factors.append({
                "type": weight_key,
                "entity_type": etype,
                "matched_value": ent["normalized_value"],
                "display_value": ent["display_value"],
                "weight": weight,
                "confidence": ent.get("confidence", 0.9),
            })

    normalized = min(100, (total_weight / max_possible) * 100) if max_possible > 0 else 0

    # Build human-readable reasons
    reason_texts = []
    for f in factors:
        readable_type = f["type"].replace("_", " ").replace("exact", "").strip()
        reason_texts.append(
            f"Same {readable_type} identifier '{f['display_value']}' appears in both cases"
        )

    return round(normalized, 2), factors, reason_texts


class CrossCaseCorrelationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def correlate_case(
        self,
        case_id: uuid.UUID,
        executed_by: uuid.UUID,
        accessible_case_ids: set[uuid.UUID] | None = None,
    ) -> list[dict[str, Any]]:
        """Compare a case against authorized cases and generate correlation leads.

        Uses indexed entity overlap — only compares cases that share at least one entity.
        If accessible_case_ids is provided, only those cases are compared.
        """
        # Get all entities in this case
        ce_stmt = select(CaseEntity).where(CaseEntity.case_id == case_id)
        ce_result = await self.db.execute(ce_stmt)
        case_entities = ce_result.scalars().all()

        if not case_entities:
            return []

        entity_ids = [ce.entity_id for ce in case_entities]

        # Load entity details
        ent_stmt = select(Entity).where(Entity.id.in_(entity_ids))
        ent_result = await self.db.execute(ent_stmt)
        entities_map = {e.id: e for e in ent_result.scalars().all()}

        # Find all other cases that share entities (indexed lookup)
        shared_stmt = (
            select(CaseEntity.case_id, CaseEntity.entity_id)
            .where(
                CaseEntity.entity_id.in_(entity_ids),
                CaseEntity.case_id != case_id,
            )
        )
        shared_result = await self.db.execute(shared_stmt)
        shared_rows = shared_result.all()

        # Group by other case, filtering to accessible cases
        other_cases: dict[uuid.UUID, list[uuid.UUID]] = {}
        for other_case_id, entity_id in shared_rows:
            # Skip if user doesn't have access to the other case
            if accessible_case_ids is not None and other_case_id not in accessible_case_ids:
                continue
            if other_case_id not in other_cases:
                other_cases[other_case_id] = []
            other_cases[other_case_id].append(entity_id)

        max_possible = sum(CROSS_CASE_WEIGHTS.values())
        generated_leads = []

        for other_case_id, shared_entity_ids in other_cases.items():
            # Build shared entity info
            shared_info = []
            for eid in shared_entity_ids:
                entity = entities_map.get(eid)
                if entity:
                    shared_info.append({
                        "entity_id": str(eid),
                        "entity_type": entity.entity_type.value if hasattr(entity.entity_type, 'value') else entity.entity_type,
                        "normalized_value": entity.normalized_value,
                        "display_value": entity.display_value,
                        "confidence": entity.confidence,
                    })

            # Compute score
            score, factors, reason_texts = _compute_correlation_score(shared_info, max_possible)

            if score <= 0:
                continue

            # Build explanation
            explanation = (
                f"Potential cross-case relationship detected based on {len(shared_entity_ids)} shared "
                f"identifier(s). This is an analytical inference requiring human verification.\n\n"
                f"Reasons:\n" + "\n".join(f"• {r}" for r in reason_texts) + "\n\n"
                f"This result is an analytical lead requiring investigator review."
            )

            priority = _score_to_priority(score)

            # Get the related case number
            case_stmt = select(Case.case_number).where(Case.id == other_case_id)
            case_result = await self.db.execute(case_stmt)
            related_case_number = case_result.scalar_one_or_none() or "Unknown"

            lead = Lead(
                case_id=case_id,
                related_case_id=other_case_id,
                lead_type="CROSS_CASE_CORRELATION",
                score=score,
                priority=priority,
                explanation=explanation,
                factors=json.dumps(factors),
                status=LeadStatus.NEW,
            )
            self.db.add(lead)
            await self.db.flush()

            generated_leads.append({
                "lead_id": str(lead.id),
                "case_id": str(case_id),
                "related_case_id": str(other_case_id),
                "related_case_number": related_case_number,
                "score": score,
                "priority": priority.value,
                "shared_entity_count": len(shared_entity_ids),
                "factors": factors,
                "reasons": reason_texts,
            })

        return generated_leads

    async def get_correlations_for_case(
        self,
        case_id: uuid.UUID,
    ) -> list[dict[str, Any]]:
        """Get existing correlation leads for a case."""
        stmt = (
            select(Lead)
            .where(Lead.case_id == case_id, Lead.lead_type == "CROSS_CASE_CORRELATION")
            .order_by(Lead.score.desc())
        )
        result = await self.db.execute(stmt)
        leads = result.scalars().all()

        correlations = []
        for lead in leads:
            # Get related case number
            case_number = "Unknown"
            if lead.related_case_id:
                case_stmt = select(Case.case_number).where(Case.id == lead.related_case_id)
                case_result = await self.db.execute(case_stmt)
                case_number = case_result.scalar_one_or_none() or "Unknown"

            factors = json.loads(lead.factors) if lead.factors else []

            correlations.append({
                "lead_id": str(lead.id),
                "related_case_id": str(lead.related_case_id) if lead.related_case_id else None,
                "related_case_number": case_number,
                "score": lead.score,
                "priority": lead.priority.value,
                "status": lead.status.value,
                "explanation": lead.explanation,
                "factors": factors,
                "created_at": lead.created_at.isoformat() if lead.created_at else None,
            })

        return correlations
