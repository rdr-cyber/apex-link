"""Cross-Case Timeline service.

Combines events from multiple authorized cases into one chronological
timeline with temporal proximity detection and cluster analysis.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.case import Case
from app.models.evidence import Evidence
from app.models.entity import Entity, CaseEntity
from app.models.lead import Lead

TEMPORAL_WINDOW_HOURS = 48
CLUSTER_WINDOW_HOURS = 18


class CrossCaseTimelineService:
    """Generates cross-case timelines from authorized cases."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_cross_case_timeline(
        self,
        case_ids: list[uuid.UUID],
        accessible_case_ids: set[uuid.UUID],
        event_type: str | None = None,
        entity_type: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict[str, Any]:
        """Build a merged timeline from multiple authorized cases.

        All requested case_ids must be in accessible_case_ids.
        """
        # Authorization check
        unauthorized = [cid for cid in case_ids if cid not in accessible_case_ids]
        if unauthorized:
            return {
                "error": "Access denied to one or more requested cases.",
                "events": [],
                "total": 0,
            }

        # Get case metadata
        case_map = await self._get_case_map(case_ids)

        # Collect events from all cases
        all_events = []
        for case_id in case_ids:
            case_number = case_map.get(case_id, {}).get("case_number", str(case_id))
            events = await self._collect_case_events(case_id, case_number)
            all_events.extend(events)

        # Sort chronologically (oldest first)
        all_events.sort(key=lambda e: e.get("timestamp", ""))

        # Apply filters
        if event_type:
            all_events = [e for e in all_events if e.get("event_type") == event_type]
        if entity_type:
            all_events = [e for e in all_events if e.get("entity_type") == entity_type]
        if date_from:
            all_events = [e for e in all_events if e.get("timestamp", "") >= date_from]
        if date_to:
            all_events = [e for e in all_events if e.get("timestamp", "") <= date_to]

        # Detect temporal proximity
        proximity_pairs = self._detect_temporal_proximity(all_events)

        # Detect temporal clusters
        clusters = self._detect_temporal_clusters(all_events)

        # Generate summary observations
        observations = self._generate_observations(
            all_events, case_ids, proximity_pairs, clusters
        )

        return {
            "case_ids": [str(cid) for cid in case_ids],
            "cases": [
                {"id": str(cid), **case_map.get(cid, {})}
                for cid in case_ids
            ],
            "events": all_events,
            "total": len(all_events),
            "temporal_proximity": proximity_pairs,
            "clusters": clusters,
            "observations": observations,
            "filters_applied": {
                "event_type": event_type,
                "entity_type": entity_type,
                "date_from": date_from,
                "date_to": date_to,
            },
        }

    async def _get_case_map(self, case_ids: list[uuid.UUID]) -> dict:
        """Get case metadata for the requested cases."""
        stmt = select(Case).where(Case.id.in_(case_ids))
        result = await self.db.execute(stmt)
        cases = result.scalars().all()

        return {
            c.id: {
                "case_number": c.case_number,
                "title": c.title,
                "category": c.category,
                "status": c.status.value if hasattr(c.status, 'value') else c.status,
            }
            for c in cases
        }

    async def _collect_case_events(self, case_id: uuid.UUID, case_number: str) -> list[dict]:
        """Collect all timestamped events from a case."""
        events = []

        # Evidence collection events
        ev_stmt = (
            select(Evidence)
            .where(Evidence.case_id == case_id, Evidence.collected_at.isnot(None))
            .order_by(Evidence.collected_at)
        )
        ev_result = await self.db.execute(ev_stmt)
        for ev in ev_result.scalars().all():
            events.append({
                "timestamp": ev.collected_at.isoformat(),
                "event_type": "EVIDENCE_COLLECTED",
                "case_id": str(case_id),
                "case_number": case_number,
                "entity_type": ev.evidence_type.value if hasattr(ev.evidence_type, 'value') else str(ev.evidence_type),
                "display_value": f"Evidence {ev.evidence_number}: {ev.filename}",
                "evidence_id": str(ev.id),
                "description": f"Collected {ev.evidence_type.value if hasattr(ev.evidence_type, 'value') else str(ev.evidence_type)} evidence",
                "source": "evidence",
            })

        # Entity link events
        ce_stmt = (
            select(CaseEntity, Entity)
            .join(Entity, CaseEntity.entity_id == Entity.id)
            .where(CaseEntity.case_id == case_id)
            .order_by(CaseEntity.created_at)
        )
        ce_result = await self.db.execute(ce_stmt)
        for ce, entity in ce_result.all():
            events.append({
                "timestamp": ce.created_at.isoformat(),
                "event_type": "ENTITY_LINKED",
                "case_id": str(case_id),
                "case_number": case_number,
                "entity_id": str(entity.id),
                "entity_type": entity.entity_type.value if hasattr(entity.entity_type, 'value') else str(entity.entity_type),
                "display_value": entity.display_value,
                "description": f"Entity {entity.display_value} linked to case",
                "source": "entity",
            })

        # Lead events
        lead_stmt = (
            select(Lead)
            .where(Lead.case_id == case_id, Lead.created_at.isnot(None))
            .order_by(Lead.created_at)
        )
        lead_result = await self.db.execute(lead_stmt)
        for lead in lead_result.scalars().all():
            events.append({
                "timestamp": lead.created_at.isoformat(),
                "event_type": "LEAD_CREATED",
                "case_id": str(case_id),
                "case_number": case_number,
                "lead_id": str(lead.id),
                "display_value": f"Lead (score: {lead.score})",
                "description": f"Analytical lead generated with score {lead.score}",
                "source": "analysis",
            })

        return events

    def _detect_temporal_proximity(self, events: list[dict]) -> list[dict]:
        """Find events from different cases that are temporally close."""
        pairs = []
        window = timedelta(hours=TEMPORAL_WINDOW_HOURS)

        for i, ev_a in enumerate(events):
            for ev_b in events[i + 1:]:
                if ev_a.get("case_id") == ev_b.get("case_id"):
                    continue
                if not ev_a.get("timestamp") or not ev_b.get("timestamp"):
                    continue

                try:
                    ts_a = datetime.fromisoformat(ev_a["timestamp"].replace("Z", "+00:00"))
                    ts_b = datetime.fromisoformat(ev_b["timestamp"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    continue

                delta = abs(ts_a - ts_b)
                if delta <= window:
                    hours = delta.total_seconds() / 3600
                    pairs.append({
                        "event_a": {
                            "timestamp": ev_a["timestamp"],
                            "case_number": ev_a.get("case_number"),
                            "event_type": ev_a.get("event_type"),
                            "display_value": ev_a.get("display_value"),
                        },
                        "event_b": {
                            "timestamp": ev_b["timestamp"],
                            "case_number": ev_b.get("case_number"),
                            "event_type": ev_b.get("event_type"),
                            "display_value": ev_b.get("display_value"),
                        },
                        "hours_apart": round(hours, 1),
                    })

        # Sort by proximity (closest first)
        pairs.sort(key=lambda p: p["hours_apart"])
        return pairs[:20]  # Limit to top 20

    def _detect_temporal_clusters(self, events: list[dict]) -> list[dict]:
        """Detect clusters of events occurring close together."""
        if len(events) < 3:
            return []

        clusters = []
        window = timedelta(hours=CLUSTER_WINDOW_HOURS)
        used = set()

        for i, ev in enumerate(events):
            if i in used:
                continue
            if not ev.get("timestamp"):
                continue

            try:
                center = datetime.fromisoformat(ev["timestamp"].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                continue

            cluster_events = [ev]
            for j, ev2 in enumerate(events):
                if j <= i or j in used:
                    continue
                if not ev2.get("timestamp"):
                    continue
                try:
                    ts = datetime.fromisoformat(ev2["timestamp"].replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    continue
                if abs(ts - center) <= window:
                    cluster_events.append(ev2)
                    used.add(j)

            if len(cluster_events) >= 3:
                case_numbers = set(e.get("case_number") for e in cluster_events)
                event_types = set(e.get("event_type") for e in cluster_events)
                clusters.append({
                    "event_count": len(cluster_events),
                    "case_numbers": sorted(case_numbers),
                    "event_types": sorted(event_types),
                    "start_time": cluster_events[0]["timestamp"],
                    "end_time": cluster_events[-1]["timestamp"],
                    "description": (
                        f"{len(cluster_events)} related events occurred across "
                        f"{len(case_numbers)} case(s) within "
                        f"{CLUSTER_WINDOW_HOURS} hours."
                    ),
                })

        return clusters

    def _generate_observations(
        self, events: list[dict], case_ids, proximity_pairs, clusters
    ) -> list[str]:
        """Generate human-readable observations about the timeline."""
        observations = []

        case_numbers = set(e.get("case_number") for e in events)
        observations.append(
            f"{len(events)} events occurred across {len(case_numbers)} case(s)."
        )

        # Count shared entities
        shared_entity_events = [
            e for e in events
            if e.get("event_type") == "ENTITY_LINKED" and e.get("entity_id")
        ]
        if shared_entity_events:
            observations.append(
                f"{len(shared_entity_events)} entity-link events were recorded."
            )

        # Temporal proximity
        if proximity_pairs:
            closest = proximity_pairs[0]
            observations.append(
                f"{len(proximity_pairs)} event pair(s) occurred within "
                f"{TEMPORAL_WINDOW_HOURS} hours. The closest pair was "
                f"{closest['hours_apart']} hours apart."
            )

        # Clusters
        if clusters:
            observations.append(
                f"{len(clusters)} temporal cluster(s) detected."
            )

        observations.append(
            "Temporal proximity is an observation and does not establish causality."
        )

        return observations
