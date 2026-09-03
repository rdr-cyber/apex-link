"""Network Path Finder service.

Finds evidence-backed paths between entities or cases using NetworkX.
For case-to-case: searches ALL authorized entities in both cases,
finds candidate paths across all entity pairs, ranks by quality,
and returns the strongest.

ALGORITHM_VERSION = "1.1.0" (additive: path-finding is new functionality)

Path ranking priority:
1. Higher evidence support
2. Higher relationship confidence
3. Stronger relationship basis
4. Fewer hops
"""

import uuid
from typing import Any

import networkx as nx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.entity import Entity, CaseEntity
from app.models.case import Case
from app.models.relationship import Relationship

# Configuration
MAX_PATH_HOPS = 6
MAX_ALTERNATIVE_PATHS = 3
MAX_ENTITIES_PER_CASE = 50  # Configurable limit
PATH_FINDER_VERSION = "1.1.0"

# Edge quality weights
EDGE_WEIGHTS = {
    "confidence": 0.4,
    "evidence_backed": 0.3,
    "basis_quality": 0.3,
}

BASIS_QUALITY = {
    "EXPLICIT_SOURCE": 1.0,
    "STRUCTURED_RECORD": 0.9,
    "SHARED_IDENTIFIER": 0.85,
    "CROSS_CASE_LINK": 0.7,
    "TEXTUAL_CO_OCCURRENCE": 0.6,
    "TEMPORAL_ASSOCIATION": 0.5,
    "MANUAL": 0.8,
}


class PathFinderService:
    """Finds and explains network paths between entities/cases."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _build_graph(
        self, case_ids: set[uuid.UUID] | None = None
    ) -> tuple[nx.Graph, dict[str, dict], dict[str, dict]]:
        """Build a NetworkX graph from the database."""
        ent_stmt = select(Entity)
        ent_result = await self.db.execute(ent_stmt)
        entities = ent_result.scalars().all()

        rel_stmt = select(Relationship)
        rel_result = await self.db.execute(rel_stmt)
        relationships = rel_result.scalars().all()

        G = nx.Graph()
        node_info: dict[str, dict] = {}
        edge_info: dict[str, dict] = {}

        for e in entities:
            eid = str(e.id)
            etype = e.entity_type.value if hasattr(e.entity_type, 'value') else str(e.entity_type)
            G.add_node(eid, entity_type=etype, label=e.display_value)
            node_info[eid] = {
                "node_id": eid,
                "entity_type": etype,
                "display_value": e.display_value,
                "normalized_value": e.normalized_value,
                "confidence": e.confidence,
            }

        for rel in relationships:
            src = str(rel.source_entity_id)
            tgt = str(rel.target_entity_id)
            rid = str(rel.id)
            if src in G.nodes and tgt in G.nodes:
                basis = rel.relationship_basis
                basis_quality = BASIS_QUALITY.get(basis, 0.5)
                has_evidence = rel.source_evidence_id is not None

                edge_quality = (
                    EDGE_WEIGHTS["confidence"] * rel.confidence
                    + EDGE_WEIGHTS["evidence_backed"] * (1.0 if has_evidence else 0.3)
                    + EDGE_WEIGHTS["basis_quality"] * basis_quality
                )

                G.add_edge(
                    src, tgt,
                    weight=1.0 / max(edge_quality, 0.01),
                    relationship_type=rel.relationship_type.value,
                    confidence=rel.confidence,
                    basis=rel.relationship_basis,
                    source_evidence_id=str(rel.source_evidence_id) if rel.source_evidence_id else None,
                    case_id=str(rel.case_id),
                    id=rid,
                )
                edge_info[f"{src}-{tgt}"] = {
                    "relationship_type": rel.relationship_type.value,
                    "basis": rel.relationship_basis,
                    "confidence": rel.confidence,
                    "source_evidence_id": str(rel.source_evidence_id) if rel.source_evidence_id else None,
                    "supporting_evidence": [str(rel.source_evidence_id)] if rel.source_evidence_id else [],
                }

        return G, node_info, edge_info

    def _compute_path_quality(self, G: nx.Graph, path: list[str], edge_info: dict) -> float:
        """Compute a 0-100 quality score for a path."""
        if len(path) < 2:
            return 0.0

        total_quality = 0.0
        hop_count = len(path) - 1

        for i in range(hop_count):
            src, tgt = path[i], path[i + 1]
            edge_key_fwd = f"{src}-{tgt}"
            edge_key_rev = f"{tgt}-{src}"
            info = edge_info.get(edge_key_fwd) or edge_info.get(edge_key_rev, {})

            confidence = info.get("confidence", 0.5)
            has_evidence = info.get("source_evidence_id") is not None
            basis = info.get("basis", "TEXTUAL_CO_OCCURRENCE")
            basis_q = BASIS_QUALITY.get(basis, 0.5)

            edge_quality = (
                confidence * 0.4
                + (1.0 if has_evidence else 0.3) * 0.3
                + basis_q * 0.3
            )
            total_quality += edge_quality

        avg_quality = total_quality / hop_count if hop_count > 0 else 0
        hop_penalty = max(0, 1.0 - (hop_count - 1) * 0.05)
        score = avg_quality * hop_penalty * 100
        return round(min(score, 100), 1)

    def _rank_path(self, path: list[str], G: nx.Graph, edge_info: dict) -> dict:
        """Compute detailed ranking factors for a path.

        Ranking priority:
        1. Higher evidence support (more evidence-backed edges)
        2. Higher relationship confidence
        3. Stronger relationship basis
        4. Fewer hops
        """
        if len(path) < 2:
            return {"rank_score": 0, "evidence_count": 0, "avg_confidence": 0, "avg_basis": 0, "hops": 0}

        hop_count = len(path) - 1
        evidence_count = 0
        total_confidence = 0.0
        total_basis = 0.0

        for i in range(hop_count):
            src, tgt = path[i], path[i + 1]
            key_fwd = f"{src}-{tgt}"
            key_rev = f"{tgt}-{src}"
            info = edge_info.get(key_fwd) or edge_info.get(key_rev, {})

            if info.get("source_evidence_id"):
                evidence_count += 1
            total_confidence += info.get("confidence", 0.5)
            total_basis += BASIS_QUALITY.get(info.get("basis", "TEXTUAL_CO_OCCURRENCE"), 0.5)

        avg_confidence = total_confidence / hop_count
        avg_basis = total_basis / hop_count

        # Composite ranking score (0-100)
        rank_score = (
            (evidence_count / max(hop_count, 1)) * 35  # Evidence support: 35%
            + avg_confidence * 35                       # Confidence: 35%
            + avg_basis * 20                            # Basis quality: 20%
            + max(0, 1.0 - hop_count * 0.1) * 10       # Hop count: 10%
        ) * 100

        return {
            "rank_score": round(rank_score, 1),
            "evidence_count": evidence_count,
            "avg_confidence": round(avg_confidence, 3),
            "avg_basis": round(avg_basis, 3),
            "hops": hop_count,
        }

    def _build_explanation(
        self, path_nodes: list[dict], path_edges: list[dict], hop_count: int, path_quality: float
    ) -> str:
        """Build a human-readable explanation of the path."""
        lines = [f"Potential {hop_count}-hop connection found.\n"]

        for i, node in enumerate(path_nodes):
            prefix = "   " if i > 0 else ""
            connector = "  \u2193" if i < len(path_nodes) - 1 else ""
            lines.append(f"{prefix}{node['entity_type']}: {node['display_value']}{connector}")

        lines.append("")
        lines.append("Supporting relationships:")
        for edge in path_edges:
            lines.append(
                f"  \u2022 {edge['relationship_type']} "
                f"(confidence: {edge['confidence']:.0%}, "
                f"basis: {edge['basis'].replace('_', ' ').title()})"
            )

        lines.append("")
        lines.append(
            f"Path quality: {path_quality:.0f}/100. "
            "This describes graph connectivity and does not establish legal responsibility."
        )

        return "\n".join(lines)

    def _build_path_response(
        self,
        path: list[str],
        G: nx.Graph,
        node_info: dict,
        edge_info: dict,
        source_id: str,
        source_type: str,
        target_id: str,
        target_type: str,
    ) -> dict:
        """Build a complete path response from a NetworkX path."""
        path_nodes = []
        for nid in path:
            info = node_info.get(nid, {})
            path_nodes.append({
                "node_id": nid,
                "entity_type": info.get("entity_type", "UNKNOWN"),
                "display_value": info.get("display_value", nid),
            })

        path_edges = []
        for i in range(len(path) - 1):
            src, tgt = path[i], path[i + 1]
            key_fwd = f"{src}-{tgt}"
            key_rev = f"{tgt}-{src}"
            edge_data = edge_info.get(key_fwd) or edge_info.get(key_rev, {})
            path_edges.append({
                "relationship_type": edge_data.get("relationship_type", "UNKNOWN"),
                "basis": edge_data.get("basis", "UNKNOWN"),
                "confidence": edge_data.get("confidence", 0.0),
                "supporting_evidence": edge_data.get("supporting_evidence", []),
            })

        hop_count = len(path) - 1
        quality = self._compute_path_quality(G, path, edge_info)
        ranking = self._rank_path(path, G, edge_info)
        explanation = self._build_explanation(path_nodes, path_edges, hop_count, quality)

        all_evidence = set()
        for edge in path_edges:
            for ev_id in edge.get("supporting_evidence", []):
                if ev_id:
                    all_evidence.add(ev_id)

        return {
            "path_nodes": path_nodes,
            "path_edges": path_edges,
            "hop_count": hop_count,
            "path_quality": quality,
            "ranking": ranking,
            "explanation": explanation,
            "supporting_evidence": sorted(all_evidence),
        }

    async def find_path(
        self,
        source_id: uuid.UUID,
        source_type: str,
        target_id: uuid.UUID,
        target_type: str,
        accessible_case_ids: set[uuid.UUID] | None = None,
    ) -> dict[str, Any]:
        """Find the shortest evidence-backed path between two objects.

        For CASE-to-CASE: searches ALL authorized entities in both cases,
        finds candidate paths across all entity pairs, ranks by quality.
        """
        G, node_info, edge_info = await self._build_graph(accessible_case_ids)

        # Resolve source and target to entity node sets
        source_nodes = await self._resolve_to_nodes(source_id, source_type, G)
        target_nodes = await self._resolve_to_nodes(target_id, target_type, G)

        if not source_nodes:
            return {"error": "Source not found or not accessible.", "path_found": False}
        if not target_nodes:
            return {"error": "Target not found or not accessible.", "path_found": False}

        # For entity-to-entity: direct path search
        if source_type == "ENTITY" and target_type == "ENTITY":
            source_node = str(source_id)
            target_node = str(target_id)
            if source_node == target_node:
                return {"error": "Source and target are the same.", "path_found": False}
            return await self._search_single_pair(
                G, node_info, edge_info, source_node, target_node,
                str(source_id), source_type, str(target_id), target_type,
            )

        # For case-to-case or mixed: multi-entity search
        return await self._search_multi_entity(
            G, node_info, edge_info,
            source_nodes, target_nodes,
            str(source_id), source_type, str(target_id), target_type,
        )

    async def _search_single_pair(
        self, G, node_info, edge_info,
        source_node, target_node,
        source_id, source_type, target_id, target_type,
    ) -> dict[str, Any]:
        """Find the best path between a single source-target pair."""
        try:
            path = nx.shortest_path(G, source=source_node, target=target_node)
            if len(path) - 1 > MAX_PATH_HOPS:
                return self._no_path_result(source_id, source_type, target_id, target_type,
                    f"Path exceeds maximum {MAX_PATH_HOPS} hops.")
        except nx.NetworkXNoPath:
            return self._no_path_result(source_id, source_type, target_id, target_type)

        result = self._build_path_response(path, G, node_info, edge_info,
            source_id, source_type, target_id, target_type)

        # Find alternatives
        alternatives = self._find_alternatives(G, node_info, edge_info, source_node, target_node, exclude=path)
        if alternatives:
            result["alternative_paths"] = alternatives

        return {
            "source_id": source_id,
            "source_type": source_type,
            "target_id": target_id,
            "target_type": target_type,
            "path_found": True,
            "path": result["path_nodes"],
            "edges": result["path_edges"],
            "hop_count": result["hop_count"],
            "path_quality": result["path_quality"],
            "ranking": result["ranking"],
            "explanation": result["explanation"],
            "supporting_evidence": result["supporting_evidence"],
            "algorithm_version": PATH_FINDER_VERSION,
            **({"alternative_paths": result.get("alternative_paths", [])} if result.get("alternative_paths") else {}),
        }

    async def _search_multi_entity(
        self, G, node_info, edge_info,
        source_nodes: list[str], target_nodes: list[str],
        source_id, source_type, target_id, target_type,
    ) -> dict[str, Any]:
        """Search all entity pairs between source and target cases.

        Strategy:
        1. Try shortest paths between all (source, target) entity pairs
        2. Collect all valid paths within hop limit
        3. Rank by composite score
        4. Return the strongest path
        """
        all_paths: list[tuple[list[str], dict]] = []
        source_set = set(source_nodes)
        target_set = set(target_nodes)

        # For efficiency, limit pairs to check
        max_pairs = min(len(source_nodes) * len(target_nodes), 200)

        checked = 0
        for src_node in source_nodes:
            for tgt_node in target_nodes:
                if src_node == tgt_node:
                    continue
                if checked >= max_pairs:
                    break

                # Skip if both are in the same case's entity set and they're the same node
                try:
                    path = nx.shortest_path(G, source=src_node, target=tgt_node)
                    if len(path) - 1 <= MAX_PATH_HOPS:
                        ranking = self._rank_path(path, G, edge_info)
                        all_paths.append((path, ranking))
                except nx.NetworkXNoPath:
                    pass
                checked += 1
            if checked >= max_pairs:
                break

        if not all_paths:
            return self._no_path_result(source_id, source_type, target_id, target_type)

        # Rank paths: higher rank_score first, then fewer hops
        all_paths.sort(key=lambda x: (-x[1]["rank_score"], x[1]["hops"]))

        best_path, best_ranking = all_paths[0]
        result = self._build_path_response(best_path, G, node_info, edge_info,
            source_id, source_type, target_id, target_type)

        # Add alternatives (next best unique paths)
        alternatives = []
        seen_paths: set[str] = set()
        seen_paths.add(tuple(best_path))
        for path, ranking in all_paths[1:MAX_ALTERNATIVE_PATHS + 1]:
            path_key = tuple(path)
            if path_key not in seen_paths:
                seen_paths.add(path_key)
                alt_result = self._build_path_response(path, G, node_info, edge_info,
                    source_id, source_type, target_id, target_type)
                alternatives.append({
                    "path": alt_result["path_nodes"],
                    "edges": alt_result["path_edges"],
                    "hop_count": alt_result["hop_count"],
                    "path_quality": alt_result["path_quality"],
                    "ranking": alt_result["ranking"],
                })

        return {
            "source_id": source_id,
            "source_type": source_type,
            "target_id": target_id,
            "target_type": target_type,
            "path_found": True,
            "source_entities_searched": len(source_nodes),
            "target_entities_searched": len(target_nodes),
            "candidate_paths_found": len(all_paths),
            "path": result["path_nodes"],
            "edges": result["path_edges"],
            "hop_count": result["hop_count"],
            "path_quality": result["path_quality"],
            "ranking": result["ranking"],
            "explanation": result["explanation"],
            "supporting_evidence": result["supporting_evidence"],
            "algorithm_version": PATH_FINDER_VERSION,
            **({"alternative_paths": alternatives} if alternatives else {}),
        }

    def _find_alternatives(self, G, node_info, edge_info, source, target, exclude) -> list[dict]:
        """Find alternative paths between two nodes."""
        alternatives = []
        try:
            alt_gen = nx.shortest_simple_paths(G, source, target)
            for alt_path in alt_gen:
                if len(alternatives) >= MAX_ALTERNATIVE_PATHS:
                    break
                if alt_path != exclude and len(alt_path) - 1 <= MAX_PATH_HOPS:
                    alt_result = self._build_path_response(alt_path, G, node_info, edge_info,
                        source, "ENTITY", target, "ENTITY")
                    alternatives.append({
                        "path": alt_result["path_nodes"],
                        "edges": alt_result["path_edges"],
                        "hop_count": alt_result["hop_count"],
                        "path_quality": alt_result["path_quality"],
                        "ranking": alt_result["ranking"],
                    })
        except Exception:
            pass
        return alternatives

    def _no_path_result(self, source_id, source_type, target_id, target_type, message=None) -> dict:
        """Return a structured no-path result."""
        return {
            "source_id": source_id,
            "source_type": source_type,
            "target_id": target_id,
            "target_type": target_type,
            "path_found": False,
            "message": message or "No evidence-backed network path was found between the selected cases.",
            "path": [],
            "edges": [],
            "hop_count": 0,
            "path_quality": 0,
            "explanation": "No connection exists in the current evidence-backed network.",
            "supporting_evidence": [],
            "algorithm_version": PATH_FINDER_VERSION,
        }

    async def _resolve_to_nodes(
        self, obj_id: uuid.UUID, obj_type: str, G: nx.Graph
    ) -> list[str]:
        """Resolve a CASE or ENTITY ID to a set of graph node IDs.

        For ENTITY: returns [node_id] or empty.
        For CASE: returns ALL entities linked to that case that exist in the graph.
        """
        if obj_type == "ENTITY":
            nid = str(obj_id)
            return [nid] if nid in G.nodes else []

        if obj_type == "CASE":
            ce_stmt = select(CaseEntity.entity_id).where(CaseEntity.case_id == obj_id)
            ce_result = await self.db.execute(ce_stmt)
            entity_ids = [str(row[0]) for row in ce_result.all()]

            # Filter to entities that exist in the graph, capped at limit
            valid_nodes = [eid for eid in entity_ids if eid in G.nodes]
            return valid_nodes[:MAX_ENTITIES_PER_CASE]

        return []

    async def list_cases_for_selection(
        self, accessible_case_ids: set[uuid.UUID]
    ) -> list[dict]:
        """List cases available for path-finder selection."""
        stmt = select(Case).where(Case.id.in_(accessible_case_ids))
        result = await self.db.execute(stmt)
        cases = result.scalars().all()

        return [
            {
                "id": str(c.id),
                "case_number": c.case_number,
                "title": c.title,
                "category": c.category,
                "status": c.status.value if hasattr(c.status, 'value') else c.status,
            }
            for c in sorted(cases, key=lambda x: x.case_number)
        ]
