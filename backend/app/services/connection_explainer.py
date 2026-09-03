"""Connection Explanation service.

Generates structured, factor-based explanations for why two cases
are analytically connected. Uses only data-derived factors — no LLM.

ALGORITHM_VERSION: additive, no change to existing scoring.
"""

import json
import uuid
from typing import Any
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.entity import Entity, CaseEntity
from app.models.evidence import Evidence
from app.models.relationship import Relationship
from app.models.lead import Lead
from app.services.path_finder import PathFinderService, PATH_FINDER_VERSION


# Factor type definitions with weights
FACTOR_TYPES = {
    "SHARED_PHONE": {"weight": 30, "description": "Shared phone identifier"},
    "SHARED_UPI": {"weight": 25, "description": "Shared UPI identifier"},
    "SHARED_EMAIL": {"weight": 20, "description": "Shared email identifier"},
    "SHARED_IP": {"weight": 15, "description": "Shared IP address"},
    "SHARED_DEVICE": {"weight": 20, "description": "Shared device identifier"},
    "SHARED_VEHICLE": {"weight": 15, "description": "Shared vehicle identifier"},
    "SHARED_ORGANIZATION": {"weight": 10, "description": "Shared organization"},
    "TEMPORAL_PROXIMITY": {"weight": 10, "description": "Temporal proximity of events"},
    "NETWORK_PATH": {"weight": 8, "description": "Network path connecting cases"},
}

TEMPORAL_WINDOW_HOURS = 48


class ConnectionExplainerService:
    """Generates structured explanations for case connections."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def explain_connection(
        self,
        case_id: uuid.UUID,
        related_case_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Generate a structured explanation for why two cases are connected."""

        # Get both cases
        case_a = await self._get_case(case_id)
        case_b = await self._get_case(related_case_id)

        if not case_a or not case_b:
            return {"error": "Case not found."}

        # Get entities for both cases
        entities_a = await self._get_case_entities(case_id)
        entities_b = await self._get_case_entities(related_case_id)

        # Find shared entities
        shared_entities = self._find_shared_entities(entities_a, entities_b)

        # Generate factors
        factors = await self._generate_factors(shared_entities, case_id, related_case_id)

        # Compute score with transparency
        raw_score = sum(f["weight"] for f in factors)
        max_possible = sum(ft["weight"] for ft in FACTOR_TYPES.values())
        normalized_score = min(100, round((raw_score / max_possible) * 100, 1)) if max_possible > 0 else 0
        normalization_method = "Factor-weight normalization: sum of factor weights / max possible weights * 100, capped at 100"

        # Get network path
        path_finder = PathFinderService(self.db)
        accessible = None
        from app.services.case_access_service import get_accessible_case_ids
        try:
            from app.models.user import User
            # We don't have user here, so pass accessible=None (path finder handles gracefully)
        except Exception:
            pass

        path_result = await path_finder.find_path(
            source_id=case_id,
            source_type="CASE",
            target_id=related_case_id,
            target_type="CASE",
        )

        # Add network path factor if path found
        if path_result.get("path_found") and path_result.get("hop_count", 0) > 0:
            hop_count = path_result["hop_count"]
            factors.append({
                "factor_type": "NETWORK_PATH",
                "description": f"A {hop_count}-hop network path connects these cases",
                "observed_value": f"{hop_count} hops",
                "weight": FACTOR_TYPES["NETWORK_PATH"]["weight"],
                "supporting_entities": [
                    n["node_id"] for n in path_result.get("path", [])
                ],
                "supporting_evidence": path_result.get("supporting_evidence", []),
                "confidence": path_result.get("path_quality", 0) / 100,
            })
            # Recompute score with path factor
            raw_score = sum(f["weight"] for f in factors)
            normalized_score = min(100, round((raw_score / max_possible) * 100, 1))

        # Collect supporting evidence IDs
        all_evidence = set()
        for f in factors:
            for ev_id in f.get("supporting_evidence", []):
                if ev_id:
                    all_evidence.add(ev_id)

        # Build explanation text
        explanation_text = self._build_explanation_text(
            case_a, case_b, factors, normalized_score, path_result
        )

        return {
            "case_id": str(case_id),
            "related_case_id": str(related_case_id),
            "case_a_number": case_a.case_number,
            "case_b_number": case_b.case_number,
            "score": normalized_score,
            "raw_score": raw_score,
            "normalized_score": normalized_score,
            "max_possible": max_possible,
            "normalization_method": normalization_method,
            "total_factors": len(factors),
            "factors": factors,
            "path": path_result if path_result.get("path_found") else None,
            "supporting_evidence": sorted(all_evidence),
            "explanation": explanation_text,
            "interpretation": (
                "These observations indicate a potential analytical relationship "
                "between the cases and should be independently reviewed by an investigator."
            ),
            "algorithm_version": PATH_FINDER_VERSION,
        }

    def _find_shared_entities(
        self, entities_a: list[dict], entities_b: list[dict]
    ) -> list[dict]:
        """Find entities shared between two cases by normalized value."""
        map_a = {}
        for e in entities_a:
            key = (e["entity_type"], e["normalized_value"])
            map_a[key] = e

        shared = []
        for e in entities_b:
            key = (e["entity_type"], e["normalized_value"])
            if key in map_a:
                shared.append({
                    "entity_type": e["entity_type"],
                    "display_value": e["display_value"],
                    "normalized_value": e["normalized_value"],
                    "entity_id_a": map_a[key]["entity_id"],
                    "entity_id_b": e["entity_id"],
                    "confidence": max(map_a[key].get("confidence", 0.9), e.get("confidence", 0.9)),
                })

        return shared

    async def _generate_factors(
        self, shared_entities: list[dict], case_id: uuid.UUID, related_case_id: uuid.UUID
    ) -> list[dict]:
        """Generate structured factors from shared entities."""
        factors = []
        seen_types = set()

        type_to_factor = {
            "PHONE": "SHARED_PHONE",
            "UPI_ID": "SHARED_UPI",
            "EMAIL": "SHARED_EMAIL",
            "IP_ADDRESS": "SHARED_IP",
            "DEVICE": "SHARED_DEVICE",
            "VEHICLE": "SHARED_VEHICLE",
            "ORGANIZATION": "SHARED_ORGANIZATION",
        }

        for shared in shared_entities:
            etype = shared["entity_type"]
            factor_type = type_to_factor.get(etype)

            if factor_type and factor_type not in seen_types:
                seen_types.add(factor_type)
                ft_info = FACTOR_TYPES[factor_type]

                # Find evidence supporting these entities
                evidence_ids = await self._find_entity_evidence(
                    uuid.UUID(shared["entity_id_a"]),
                    uuid.UUID(shared["entity_id_b"]),
                )

                factors.append({
                    "factor_type": factor_type,
                    "description": ft_info["description"],
                    "observed_value": shared["display_value"],
                    "weight": ft_info["weight"],
                    "supporting_entities": [shared["entity_id_a"], shared["entity_id_b"]],
                    "supporting_evidence": evidence_ids,
                    "confidence": shared.get("confidence", 0.9),
                })

        # Check temporal proximity
        temporal_factor = await self._check_temporal_proximity(case_id, related_case_id)
        if temporal_factor:
            factors.append(temporal_factor)

        # Sort by weight descending
        factors.sort(key=lambda f: f["weight"], reverse=True)
        return factors

    async def _find_entity_evidence(
        self, entity_id_a: uuid.UUID, entity_id_b: uuid.UUID
    ) -> list[str]:
        """Find evidence IDs that reference either entity."""
        from app.models.entity import CaseEntity
        evidence_ids = []

        for eid in [entity_id_a, entity_id_b]:
            ce_stmt = select(CaseEntity.source_evidence_id).where(
                CaseEntity.entity_id == eid,
                CaseEntity.source_evidence_id.isnot(None),
            )
            result = await self.db.execute(ce_stmt)
            for row in result.all():
                if row[0]:
                    evidence_ids.append(str(row[0]))

        return list(set(evidence_ids))

    async def _check_temporal_proximity(
        self, case_id: uuid.UUID, related_case_id: uuid.UUID
    ) -> dict | None:
        """Check if events from both cases occur within the temporal window."""
        from app.models.entity import CaseEntity
        from datetime import timedelta

        # Get evidence with timestamps from both cases
        events = []
        for cid in [case_id, related_case_id]:
            ev_stmt = select(Evidence.collected_at).where(
                Evidence.case_id == cid,
                Evidence.collected_at.isnot(None),
            )
            result = await self.db.execute(ev_stmt)
            for row in result.all():
                if row[0]:
                    events.append({"case_id": str(cid), "timestamp": row[0]})

        if len(events) < 2:
            return None

        # Find closest pair across cases
        closest_delta = None
        for i, ev_a in enumerate(events):
            for ev_b in events[i + 1:]:
                if ev_a["case_id"] != ev_b["case_id"]:
                    delta = abs(ev_a["timestamp"] - ev_b["timestamp"])
                    if closest_delta is None or delta < closest_delta:
                        closest_delta = delta

        if closest_delta is None:
            return None

        window = timedelta(hours=TEMPORAL_WINDOW_HOURS)
        if closest_delta <= window:
            hours = closest_delta.total_seconds() / 3600
            return {
                "factor_type": "TEMPORAL_PROXIMITY",
                "description": f"Events occurred within {hours:.1f} hours of each other",
                "observed_value": f"{hours:.1f} hours",
                "weight": FACTOR_TYPES["TEMPORAL_PROXIMITY"]["weight"],
                "supporting_entities": [],
                "supporting_evidence": [],
                "confidence": max(0.5, 1.0 - hours / TEMPORAL_WINDOW_HOURS),
            }

        return None

    async def _get_case(self, case_id: uuid.UUID) -> Case | None:
        result = await self.db.execute(select(Case).where(Case.id == case_id))
        return result.scalar_one_or_none()

    async def _get_case_entities(self, case_id: uuid.UUID) -> list[dict]:
        """Get all entities for a case with their details."""
        ce_stmt = select(CaseEntity).where(CaseEntity.case_id == case_id)
        ce_result = await self.db.execute(ce_stmt)
        case_entities = ce_result.scalars().all()

        if not case_entities:
            return []

        entity_ids = [ce.entity_id for ce in case_entities]
        ent_stmt = select(Entity).where(Entity.id.in_(entity_ids))
        ent_result = await self.db.execute(ent_stmt)
        entity_map = {e.id: e for e in ent_result.scalars().all()}

        return [
            {
                "entity_id": str(ce.entity_id),
                "entity_type": entity_map[ce.entity_id].entity_type.value
                    if hasattr(entity_map[ce.entity_id].entity_type, 'value')
                    else str(entity_map[ce.entity_id].entity_type),
                "display_value": entity_map[ce.entity_id].display_value,
                "normalized_value": entity_map[ce.entity_id].normalized_value,
                "confidence": ce.confidence,
            }
            for ce in case_entities
            if ce.entity_id in entity_map
        ]

    def _build_explanation_text(
        self, case_a, case_b, factors, score, path_result
    ) -> str:
        """Build a human-readable explanation."""
        lines = [
            f"WHY ARE THESE CASES CONNECTED?\n",
            f"Cases: {case_a.case_number} \u2194 {case_b.case_number}",
            f"Connection strength: {score}/100\n",
        ]

        for i, f in enumerate(factors, 1):
            lines.append(f"{i}. {f['description']}")
            lines.append(f"   Observed: {f['observed_value']}")
            lines.append(f"   Contribution: +{f['weight']} points")
            if f.get("supporting_evidence"):
                lines.append(f"   Evidence: {', '.join(f['supporting_evidence'][:5])}")
            lines.append("")

        if path_result and path_result.get("path_found"):
            hop_count = path_result["hop_count"]
            lines.append(f"Network path: {hop_count}-hop connection through shared identifiers.")

        lines.append("\nINTERPRETATION")
        lines.append(
            "These observations indicate a potential analytical relationship "
            "between the cases and should be independently reviewed."
        )
        lines.append(
            "This analysis is decision support. It does not establish criminal responsibility."
        )

        return "\n".join(lines)
