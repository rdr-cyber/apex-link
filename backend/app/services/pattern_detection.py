"""
Pattern Detection Service
Implements explainable suspicious-pattern rules.

Patterns:
A — Multi-case identifier
B — Bridge entity
C — Fan-out
D — Fan-in
E — Burst activity
"""
from __future__ import annotations

import enum
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity, CaseEntity
from app.models.evidence import Evidence
from app.models.relationship import Relationship
from app.core.config import SUSPICIOUS_PATTERNS

logger = logging.getLogger(__name__)


class PatternType(str, enum.Enum):
    MULTI_CASE = "MULTI_CASE_IDENTIFIER"
    BRIDGE = "BRIDGE_ENTITY"
    FAN_OUT = "FAN_OUT"
    FAN_IN = "FAN_IN"
    BURST = "BURST_ACTIVITY"
    SHARED_INFRASTRUCTURE = "SHARED_INFRASTRUCTURE"


def _to_serializable(obj: Any) -> Any:
    """Make values JSON-serializable."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, (list, tuple)):
        return [_to_serializable(v) for v in obj]
    if isinstance(obj, dict):
        return {k: _to_serializable(v) for k, v in obj.items()}
    return obj


class PatternDetectionService:
    """Detects explainable suspicious patterns in entity/relationship data."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def detect_all_patterns(self, case_id: Any = None) -> list[dict]:
        """Run all pattern detections, optionally scoped to a case."""
        patterns: list[dict] = []
        patterns.extend(await self.detect_multi_case_identifiers(case_id))
        patterns.extend(await self.detect_bridge_entities(case_id))
        patterns.extend(await self.detect_fan_out(case_id))
        patterns.extend(await self.detect_fan_in(case_id))
        patterns.extend(await self.detect_burst_activity(case_id))
        return patterns

    async def detect_multi_case_identifiers(
        self, case_id: Any = None
    ) -> list[dict]:
        """Pattern A: An exact entity appears in many cases."""
        threshold = SUSPICIOUS_PATTERNS["multi_case"]["min_cases"]

        # Find entities appearing in multiple cases.
        # When case_id is specified, first find entities in that case,
        # then count across ALL cases (not just the target).
        entity_in_case_subq = None
        if case_id is not None:
            entity_in_case_subq = (
                select(CaseEntity.entity_id)
                .where(CaseEntity.case_id == case_id)
                .distinct()
                .subquery()
            )

        stmt = (
            select(
                CaseEntity.entity_id,
                func.count(func.distinct(CaseEntity.case_id)).label("case_count"),
            )
            .group_by(CaseEntity.entity_id)
            .having(func.count(func.distinct(CaseEntity.case_id)) >= threshold)
        )

        # If case_id specified, restrict to entities that appear in that case
        if entity_in_case_subq is not None:
            stmt = stmt.where(CaseEntity.entity_id.in_(select(entity_in_case_subq.c.entity_id)))

        result = await self.db.execute(stmt)
        rows = result.all()

        patterns = []
        for entity_id, case_count in rows:
            entity = await self.db.get(Entity, entity_id)
            if not entity:
                continue

            # Get the case IDs
            ce_stmt = (
                select(CaseEntity.case_id)
                .where(CaseEntity.entity_id == entity_id)
                .distinct()
            )
            ce_result = await self.db.execute(ce_stmt)
            case_ids = [row[0] for row in ce_result.all()]

            # Get evidence supporting this
            ev_stmt = (
                select(CaseEntity.source_evidence_id)
                .where(CaseEntity.entity_id == entity_id)
                .distinct()
            )
            ev_result = await self.db.execute(ev_stmt)
            evidence_ids = [
                row[0] for row in ev_result.all() if row[0] is not None
            ]

            patterns.append(
                {
                    "pattern_type": PatternType.MULTI_CASE.value,
                    "entity_id": str(entity_id),
                    "entity_type": entity.entity_type.value,
                    "display_value": entity.display_value,
                    "observed_value": case_count,
                    "threshold": threshold,
                    "case_count": case_count,
                    "case_ids": [str(cid) for cid in case_ids],
                    "supporting_evidence": [str(eid) for eid in evidence_ids],
                    "confidence": min(0.95, 0.5 + case_count * 0.1),
                    "explanation": (
                        f"Entity '{entity.display_value}' ({entity.entity_type.value}) "
                        f"appears in {case_count} cases "
                        f"(threshold: {threshold}). "
                        f"Multi-case presence may indicate a recurring identifier "
                        f"requiring investigator review."
                    ),
                }
            )

        return patterns

    async def detect_bridge_entities(
        self, case_id: Any = None
    ) -> list[dict]:
        """Pattern B: Entity connects otherwise separated clusters."""
        from app.services.graph_service import GraphService

        graph_service = GraphService(self.db)
        graph_result = await graph_service.build_and_analyze(case_id)

        if not graph_result.nodes:
            return []

        patterns = []
        node_map = {n.id: n for n in graph_result.nodes}

        # Identify communities using connected components via adjacency
        adjacency: dict[str, set[str]] = defaultdict(set)
        for edge in graph_result.edges:
            adjacency[edge.source].add(edge.target)
            adjacency[edge.target].add(edge.source)

        # Find connected components
        visited: set[str] = set()
        components: list[set[str]] = []

        all_nodes = {n.id for n in graph_result.nodes}
        for node_id in all_nodes:
            if node_id in visited:
                continue
            component: set[str] = set()
            stack = [node_id]
            while stack:
                current = stack.pop()
                if current in visited:
                    continue
                visited.add(current)
                component.add(current)
                for neighbor in adjacency.get(current, set()):
                    if neighbor not in visited:
                        stack.append(neighbor)
            if component:
                components.append(component)

        if len(components) < 2:
            return []

        # An entity is a bridge if it has edges to nodes in 2+ components
        for entity_id in adjacency:
            connected_components = set()
            for neighbor in adjacency[entity_id]:
                for i, comp in enumerate(components):
                    if neighbor in comp:
                        connected_components.add(i)
                        break

            if len(connected_components) >= 2:
                node = node_map.get(entity_id)
                patterns.append(
                    {
                        "pattern_type": PatternType.BRIDGE.value,
                        "entity_id": entity_id,
                        "entity_type": node.entity_type if node else "UNKNOWN",
                        "display_value": node.label if node else entity_id,
                        "observed_value": len(connected_components),
                        "threshold": 2,
                        "cluster_count": len(connected_components),
                        "confidence": min(0.95, 0.6 + len(connected_components) * 0.1),
                        "explanation": (
                            f"Entity '{node.label if node else entity_id}' "
                            f"connects {len(connected_components)} otherwise-separated "
                            f"clusters. This may indicate a bridge entity linking "
                            f"different network segments requiring investigator review."
                        ),
                    }
                )

        return patterns

    async def detect_fan_out(self, case_id: Any = None) -> list[dict]:
        """Pattern C: One source connects to unusually many targets."""
        threshold = SUSPICIOUS_PATTERNS["fan_out"]["min_recipients"]

        # Count outgoing relationships per entity
        stmt = (
            select(
                Relationship.source_entity_id,
                func.count(Relationship.id).label("out_degree"),
            )
            .group_by(Relationship.source_entity_id)
            .having(func.count(Relationship.id) >= threshold)
        )

        if case_id is not None:
            stmt = stmt.where(Relationship.case_id == case_id)

        result = await self.db.execute(stmt)
        rows = result.all()

        patterns = []
        for entity_id, out_degree in rows:
            entity = await self.db.get(Entity, entity_id)
            if not entity:
                continue

            patterns.append(
                {
                    "pattern_type": PatternType.FAN_OUT.value,
                    "entity_id": str(entity_id),
                    "entity_type": entity.entity_type.value,
                    "display_value": entity.display_value,
                    "observed_value": out_degree,
                    "threshold": threshold,
                    "confidence": min(0.90, 0.5 + (out_degree - threshold) * 0.05),
                    "explanation": (
                        f"Entity '{entity.display_value}' ({entity.entity_type.value}) "
                        f"has {out_degree} outgoing connections "
                        f"(threshold: {threshold}). "
                        f"High fan-out may indicate broad connectivity requiring review."
                    ),
                }
            )

        return patterns

    async def detect_fan_in(self, case_id: Any = None) -> list[dict]:
        """Pattern D: Many sources converge on one target."""
        threshold = SUSPICIOUS_PATTERNS["fan_in"]["min_sources"]

        stmt = (
            select(
                Relationship.target_entity_id,
                func.count(Relationship.id).label("in_degree"),
            )
            .group_by(Relationship.target_entity_id)
            .having(func.count(Relationship.id) >= threshold)
        )

        if case_id is not None:
            stmt = stmt.where(Relationship.case_id == case_id)

        result = await self.db.execute(stmt)
        rows = result.all()

        patterns = []
        for entity_id, in_degree in rows:
            entity = await self.db.get(Entity, entity_id)
            if not entity:
                continue

            patterns.append(
                {
                    "pattern_type": PatternType.FAN_IN.value,
                    "entity_id": str(entity_id),
                    "entity_type": entity.entity_type.value,
                    "display_value": entity.display_value,
                    "observed_value": in_degree,
                    "threshold": threshold,
                    "confidence": min(0.90, 0.5 + (in_degree - threshold) * 0.05),
                    "explanation": (
                        f"Entity '{entity.display_value}' ({entity.entity_type.value}) "
                        f"has {in_degree} incoming connections "
                        f"(threshold: {threshold}). "
                        f"High fan-in may indicate a convergence point requiring review."
                    ),
                }
            )

        return patterns

    async def detect_burst_activity(
        self, case_id: Any = None
    ) -> list[dict]:
        """Pattern E: Many events involving the same entity within a short time window."""
        window_hours = SUSPICIOUS_PATTERNS["burst"]["window_hours"]
        threshold = SUSPICIOUS_PATTERNS["burst"]["min_events"]
        cutoff = datetime.now(timezone.utc) - timedelta(hours=window_hours)

        # Count entity mentions within the time window
        stmt = (
            select(
                CaseEntity.entity_id,
                func.count(CaseEntity.id).label("mention_count"),
            )
            .where(CaseEntity.created_at >= cutoff)
            .group_by(CaseEntity.entity_id)
            .having(func.count(CaseEntity.id) >= threshold)
        )

        if case_id is not None:
            stmt = stmt.where(CaseEntity.case_id == case_id)

        result = await self.db.execute(stmt)
        rows = result.all()

        patterns = []
        for entity_id, mention_count in rows:
            entity = await self.db.get(Entity, entity_id)
            if not entity:
                continue

            patterns.append(
                {
                    "pattern_type": PatternType.BURST.value,
                    "entity_id": str(entity_id),
                    "entity_type": entity.entity_type.value,
                    "display_value": entity.display_value,
                    "observed_value": mention_count,
                    "threshold": threshold,
                    "window_hours": window_hours,
                    "confidence": min(0.90, 0.5 + (mention_count - threshold) * 0.03),
                    "explanation": (
                        f"Entity '{entity.display_value}' ({entity.entity_type.value}) "
                        f"appeared {mention_count} times within the last {window_hours} hours "
                        f"(threshold: {threshold}). "
                        f"Burst activity may indicate concentrated events requiring review."
                    ),
                }
            )

        return patterns
