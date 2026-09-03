"""Analysis orchestration service.

Runs the full analysis pipeline: entity extraction, relationship generation,
graph analysis, lead generation, and suspicious pattern detection.
Results are stored for reproducibility.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ALGORITHM_VERSION
from app.models.analysis_result import AnalysisResult
from app.models.case import Case, CaseStatus
from app.models.entity import Entity, EntityType, CaseEntity
from app.models.entity_mention import EntityMention, ExtractionMethod
from app.models.evidence import Evidence
from app.models.relationship import Relationship, RelationshipType
from app.repositories.entity_repo import EntityRepository, CaseEntityRepository
from app.repositories.relationship_repo import RelationshipRepository
from app.services.entity_extraction import extract_entities_from_text
from app.services.entity_resolution import should_merge_entities
from app.services.graph_service import GraphService
from app.services.lead_service import LeadService


class AnalysisService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.entity_repo = EntityRepository(db)
        self.case_entity_repo = CaseEntityRepository(db)
        self.rel_repo = RelationshipRepository(db)

    async def extract_entities_from_evidence(
        self,
        evidence_id: uuid.UUID,
        case_id: uuid.UUID,
        extraction_method: str = ExtractionMethod.REGEX.value,
    ) -> dict[str, Any]:
        """Extract entities from evidence text, normalize, deduplicate, and link to case."""
        evidence_result = await self.db.execute(select(Evidence).where(Evidence.id == evidence_id))
        evidence = evidence_result.scalar_one_or_none()
        if evidence is None:
            raise ValueError(f"Evidence {evidence_id} not found.")

        try:
            with open(evidence.storage_path, "r", errors="replace") as f:
                text = f.read(100_000)
        except (FileNotFoundError, UnicodeDecodeError):
            text = evidence.description or ""

        extracted = extract_entities_from_text(text)

        total_new = 0
        total_linked = 0
        valid_entity_types = [t.value for t in EntityType]

        for ext in extracted:
            # Skip non-entity types (MONEY, DATE are informational only)
            if ext.entity_type not in valid_entity_types:
                mention = EntityMention(
                    evidence_id=evidence_id,
                    entity_type=ext.entity_type,
                    raw_text=ext.raw_text,
                    normalized_value=ext.normalized_value,
                    confidence=ext.confidence,
                    extraction_method=extraction_method,
                )
                self.db.add(mention)
                continue

            # Find or create entity (deduplication via normalized value)
            entity = await self.entity_repo.find_by_normalized(ext.entity_type, ext.normalized_value)
            if entity is None:
                entity = await self.entity_repo.create(
                    entity_type=ext.entity_type,
                    canonical_value=ext.raw_text,
                    display_value=ext.raw_text,
                    normalized_value=ext.normalized_value,
                    confidence=ext.confidence,
                )
                total_new += 1

            # Link entity to case if not already linked
            existing_link = await self.case_entity_repo.get_by_case_and_entity(case_id, entity.id)
            if existing_link is None:
                await self.case_entity_repo.create(
                    case_id=case_id,
                    entity_id=entity.id,
                    source_evidence_id=evidence_id,
                    mention_text=ext.raw_text,
                    confidence=ext.confidence,
                )
                total_linked += 1

            # Record mention with extraction method
            mention = EntityMention(
                evidence_id=evidence_id,
                entity_type=ext.entity_type,
                raw_text=ext.raw_text,
                normalized_value=ext.normalized_value,
                confidence=ext.confidence,
                extraction_method=extraction_method,
            )
            self.db.add(mention)

        await self.db.flush()

        return {
            "evidence_id": str(evidence_id),
            "total_extracted": len(extracted),
            "total_new": total_new,
            "total_linked": total_linked,
        }

    async def generate_relationships(self, case_id: uuid.UUID) -> int:
        """Generate relationships between entities in a case based on shared evidence."""
        ce_stmt = select(CaseEntity).where(CaseEntity.case_id == case_id)
        ce_result = await self.db.execute(ce_stmt)
        case_entities = ce_result.scalars().all()

        if len(case_entities) < 2:
            return 0

        # Group by source evidence to find co-occurring entities
        evidence_groups: dict[uuid.UUID, list[uuid.UUID]] = {}
        for ce in case_entities:
            if ce.source_evidence_id:
                if ce.source_evidence_id not in evidence_groups:
                    evidence_groups[ce.source_evidence_id] = []
                evidence_groups[ce.source_evidence_id].append(ce.entity_id)

        all_entity_ids = list(set(ce.entity_id for ce in case_entities))
        ent_stmt = select(Entity).where(Entity.id.in_(all_entity_ids))
        ent_result = await self.db.execute(ent_stmt)
        entity_map = {e.id: e for e in ent_result.scalars().all()}

        rel_count = 0

        for evidence_id, entity_ids in evidence_groups.items():
            for i in range(len(entity_ids)):
                for j in range(i + 1, len(entity_ids)):
                    eid_a, eid_b = entity_ids[i], entity_ids[j]
                    entity_a = entity_map.get(eid_a)
                    entity_b = entity_map.get(eid_b)
                    if not entity_a or not entity_b:
                        continue

                    rel_type = self._infer_relationship_type(entity_a.entity_type, entity_b.entity_type)
                    if rel_type is None:
                        rel_type = RelationshipType.MENTIONED_WITH

                    existing = await self.rel_repo.find_existing(eid_a, eid_b, rel_type.value, case_id)
                    if existing is None:
                        existing_reverse = await self.rel_repo.find_existing(eid_b, eid_a, rel_type.value, case_id)
                        if existing_reverse is None:
                            await self.rel_repo.create(
                                source_entity_id=eid_a,
                                target_entity_id=eid_b,
                                relationship_type=rel_type,
                                confidence=0.8,
                                case_id=case_id,
                                source_evidence_id=evidence_id,
                                description=f"Co-occurring entities in evidence {evidence_id}",
                            )
                            rel_count += 1

        await self._detect_cross_case_relationships(case_id)
        return rel_count

    def _infer_relationship_type(self, type_a: EntityType, type_b: EntityType) -> RelationshipType | None:
        """Infer relationship type from entity type pairs."""
        pairs = {
            (EntityType.PERSON, EntityType.PHONE): RelationshipType.USES_PHONE,
            (EntityType.PERSON, EntityType.EMAIL): RelationshipType.USES_EMAIL,
            (EntityType.PERSON, EntityType.IP_ADDRESS): RelationshipType.ASSOCIATED_WITH_IP,
            (EntityType.PERSON, EntityType.UPI_ID): RelationshipType.USES_UPI,
            (EntityType.PERSON, EntityType.DEVICE): RelationshipType.USES_DEVICE,
            (EntityType.PERSON, EntityType.LOCATION): RelationshipType.LOCATED_AT,
            (EntityType.PERSON, EntityType.ORGANIZATION): RelationshipType.MEMBER_OF,
        }
        pair = (type_a, type_b)
        if pair in pairs:
            return pairs[pair]
        reverse = (type_b, type_a)
        if reverse in pairs:
            return pairs[reverse]
        return None

    async def _detect_cross_case_relationships(self, case_id: uuid.UUID) -> None:
        """Find entities that appear in other cases and create cross-case relationships."""
        ce_stmt = select(CaseEntity.entity_id).where(CaseEntity.case_id == case_id)
        ce_result = await self.db.execute(ce_stmt)
        entity_ids = [row[0] for row in ce_result.all()]

        if not entity_ids:
            return

        cross_stmt = (
            select(CaseEntity.case_id, CaseEntity.entity_id)
            .where(
                CaseEntity.entity_id.in_(entity_ids),
                CaseEntity.case_id != case_id,
            )
        )
        cross_result = await self.db.execute(cross_stmt)
        cross_rows = cross_result.all()

        seen: set[tuple[uuid.UUID, uuid.UUID, uuid.UUID]] = set()
        for other_case_id, entity_id in cross_rows:
            key = (other_case_id, entity_id, case_id)
            if key in seen:
                continue
            seen.add(key)

            existing = await self.rel_repo.find_existing(
                entity_id, entity_id, "APPEARS_IN_CASE", other_case_id
            )
            if existing is None:
                await self.rel_repo.create(
                    source_entity_id=entity_id,
                    target_entity_id=entity_id,
                    relationship_type=RelationshipType.APPEARS_IN_CASE,
                    confidence=1.0,
                    case_id=other_case_id,
                    description=f"Entity also appears in case {case_id}",
                )

    async def run_full_analysis(self, case_id: uuid.UUID, executed_by: uuid.UUID) -> dict[str, Any]:
        """Run the complete analysis pipeline for a case."""
        ev_stmt = select(Evidence.id).where(Evidence.case_id == case_id)
        ev_result = await self.db.execute(ev_stmt)
        evidence_ids = [row[0] for row in ev_result.all()]

        extraction_results = []
        for eid in evidence_ids:
            try:
                result = await self.extract_entities_from_evidence(eid, case_id)
                extraction_results.append(result)
            except Exception as e:
                extraction_results.append({"evidence_id": str(eid), "error": str(e)})

        rel_count = await self.generate_relationships(case_id)

        graph_service = GraphService(self.db)
        graph = await graph_service.build_and_analyze(case_id)

        lead_service = LeadService(self.db)
        leads = await lead_service.generate_cross_case_leads(case_id, executed_by)

        patterns = await graph_service.detect_suspicious_patterns(case_id)
        key_entities = await graph_service.get_key_entities(case_id)

        case_result = await self.db.execute(select(Case).where(Case.id == case_id))
        case = case_result.scalar_one()
        if case:
            case.status = CaseStatus.ANALYSIS
            await self.db.flush()

        result_summary = json.dumps({
            "extraction": extraction_results,
            "relationships_generated": rel_count,
            "graph_nodes": graph.stats.get("node_count", 0),
            "graph_edges": graph.stats.get("edge_count", 0),
            "leads_generated": len(leads),
            "patterns_detected": len(patterns),
            "key_entities": len(key_entities),
        })

        analysis = AnalysisResult(
            case_id=case_id,
            executed_by=executed_by,
            algorithm_version=ALGORITHM_VERSION,
            configuration_version="1.0.0",
            result_summary=result_summary,
            status="completed",
        )
        self.db.add(analysis)
        await self.db.flush()

        return {
            "analysis_id": str(analysis.id),
            "case_id": str(case_id),
            "algorithm_version": ALGORITHM_VERSION,
            "extraction_results": extraction_results,
            "relationships_generated": rel_count,
            "graph": {
                "nodes": len(graph.nodes),
                "edges": len(graph.edges),
                "stats": graph.stats,
            },
            "leads": leads,
            "suspicious_patterns": patterns,
            "key_entities": key_entities,
        }
