"""Graph analysis service using NetworkX.

Builds a graph from entities and relationships, computes centrality metrics,
detects communities, identifies bridge entities, and finds suspicious patterns.
"""

import uuid
from typing import Any

import networkx as nx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import KEY_ENTITY_WEIGHTS, SUSPICIOUS_PATTERNS
from app.models.entity import Entity, CaseEntity
from app.models.relationship import Relationship
from app.schemas.relationship import GraphNode, GraphEdge, GraphResponse

import asyncio
from concurrent.futures import ThreadPoolExecutor

_executor = ThreadPoolExecutor(max_workers=2)


def _compute_metrics_sync(G: nx.Graph) -> dict:
    """Synchronous graph metric computation — runs in a thread pool."""
    degree = nx.degree_centrality(G)
    betweenness = nx.betweenness_centrality(G, normalized=True)
    closeness = {}
    try:
        closeness = nx.closeness_centrality(G)
    except Exception:
        pass

    communities: list[list[str]] = []
    try:
        from networkx.algorithms.community import greedy_modularity_communities
        comm_result = greedy_modularity_communities(G)
        communities = [list(c) for c in comm_result]
    except Exception:
        # Fallback: treat each connected component as a community
        for comp in nx.connected_components(G):
            communities.append(list(comp))

    connected_components = [list(c) for c in nx.connected_components(G)]

    return {
        "degree": degree,
        "betweenness": betweenness,
        "closeness": closeness,
        "communities": communities,
        "connected_components": connected_components,
    }


class GraphService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def build_and_analyze(self, case_id: uuid.UUID | None = None) -> GraphResponse:
        """Build a graph from the database and compute analysis metrics.

        If case_id is provided, only include entities/relationships for that case.
        Otherwise, build a global graph.
        """
        # Load data
        from sqlalchemy import select

        if case_id:
            # Get entities for this case
            ce_stmt = select(CaseEntity.entity_id).where(CaseEntity.case_id == case_id)
            ce_result = await self.db.execute(ce_stmt)
            entity_ids = [row[0] for row in ce_result.all()]

            if not entity_ids:
                return GraphResponse(nodes=[], edges=[], stats={"node_count": 0, "edge_count": 0})

            ent_stmt = select(Entity).where(Entity.id.in_(entity_ids))
            ent_result = await self.db.execute(ent_stmt)
            entities = ent_result.scalars().all()

            rel_stmt = select(Relationship).where(Relationship.case_id == case_id)
            rel_result = await self.db.execute(rel_stmt)
            relationships = rel_result.scalars().all()
        else:
            ent_result = await self.db.execute(select(Entity))
            entities = ent_result.scalars().all()

            rel_result = await self.db.execute(select(Relationship))
            relationships = rel_result.scalars().all()

        if not entities:
            return GraphResponse(nodes=[], edges=[], stats={"node_count": 0, "edge_count": 0})

        # Build NetworkX graph
        G = nx.Graph()
        entity_map: dict[uuid.UUID, Entity] = {}

        for e in entities:
            entity_map[e.id] = e
            G.add_node(str(e.id), entity_type=e.entity_type, label=e.display_value)

        for rel in relationships:
            src = str(rel.source_entity_id)
            tgt = str(rel.target_entity_id)
            if src in G.nodes and tgt in G.nodes:
                G.add_edge(
                    src, tgt,
                    relationship_type=rel.relationship_type,
                    confidence=rel.confidence,
                    id=str(rel.id),
                    label=rel.relationship_type,
                )

        # Compute metrics — use thread pool only for large graphs
        if G.number_of_nodes() > 50:
            loop = asyncio.get_running_loop()
            metrics = await loop.run_in_executor(_executor, _compute_metrics_sync, G)
        else:
            metrics = _compute_metrics_sync(G)

        # Get case numbers for each entity
        entity_cases_map: dict[str, list[str]] = {}
        if not case_id:
            ce_all_stmt = select(CaseEntity)
            ce_all_result = await self.db.execute(ce_all_stmt)
            all_ce = ce_all_result.scalars().all()

            from app.models.case import Case
            case_id_to_number: dict[uuid.UUID, str] = {}
            for ce in all_ce:
                if str(ce.entity_id) not in entity_cases_map:
                    entity_cases_map[str(ce.entity_id)] = []
                if ce.case_id not in case_id_to_number:
                    case_result = await self.db.execute(select(Case.case_number).where(Case.id == ce.case_id))
                    case_num = case_result.scalar_one_or_none()
                    case_id_to_number[ce.case_id] = case_num or str(ce.case_id)
                if case_id_to_number[ce.case_id] not in entity_cases_map[str(ce.entity_id)]:
                    entity_cases_map[str(ce.entity_id)].append(case_id_to_number[ce.case_id])
        else:
            from app.models.case import Case
            case_result = await self.db.execute(select(Case.case_number).where(Case.id == case_id))
            case_num = case_result.scalar_one_or_none() or str(case_id)
            for node_id in G.nodes:
                entity_cases_map[node_id] = [case_num]

        # Build response
        graph_nodes = []
        for node_id in G.nodes:
            e = entity_map.get(uuid.UUID(node_id))
            if e is None:
                continue
            graph_nodes.append(
                GraphNode(
                    id=node_id,
                    label=e.display_value,
                    entity_type=e.entity_type,
                    confidence=e.confidence,
                    degree=round(metrics["degree"].get(node_id, 0) * 100, 1),
                    betweenness=round(metrics["betweenness"].get(node_id, 0) * 100, 1),
                    closeness=round(metrics["closeness"].get(node_id, 0) * 100, 1),
                    cases=entity_cases_map.get(node_id, []),
                )
            )

        graph_edges = []
        for rel in relationships:
            src = str(rel.source_entity_id)
            tgt = str(rel.target_entity_id)
            if src in G.nodes and tgt in G.nodes:
                graph_edges.append(
                    GraphEdge(
                        id=str(rel.id),
                        source=src,
                        target=tgt,
                        relationship_type=rel.relationship_type,
                        confidence=rel.confidence,
                        label=rel.relationship_type,
                    )
                )

        stats = {
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "connected_components": len(metrics["connected_components"]),
            "communities": len(metrics["communities"]),
        }

        return GraphResponse(nodes=graph_nodes, edges=graph_edges, stats=stats)

    async def get_key_entities(self, case_id: uuid.UUID, top_n: int = 10) -> list[dict[str, Any]]:
        """Identify key entities using weighted centrality scores."""
        graph = await self.build_and_analyze(case_id)
        if not graph.nodes:
            return []

        # Normalize metrics
        max_degree = max((n.degree for n in graph.nodes), default=1) or 1
        max_betweenness = max((n.betweenness for n in graph.nodes), default=1) or 1

        # Count cross-case presence
        cross_case_count: dict[str, int] = {}
        for n in graph.nodes:
            cross_case_count[n.id] = len(n.cases)
        max_cross_case = max(cross_case_count.values(), default=1) or 1

        scored = []
        for n in graph.nodes:
            norm_degree = (n.degree / max_degree) * 100
            norm_betweenness = (n.betweenness / max_betweenness) * 100
            norm_cross = (cross_case_count.get(n.id, 0) / max_cross_case) * 100

            score = (
                KEY_ENTITY_WEIGHTS["degree"] * norm_degree
                + KEY_ENTITY_WEIGHTS["betweenness"] * norm_betweenness
                + KEY_ENTITY_WEIGHTS["cross_case"] * norm_cross
            )

            scored.append({
                "entity_id": n.id,
                "label": n.label,
                "entity_type": n.entity_type,
                "score": round(score, 2),
                "factors": {
                    "degree": round(norm_degree, 1),
                    "betweenness": round(norm_betweenness, 1),
                    "cross_case": round(norm_cross, 1),
                },
                "cases": n.cases,
            })

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_n]

    async def detect_suspicious_patterns(self, case_id: uuid.UUID | None = None) -> list[dict[str, Any]]:
        """Detect configurable suspicious patterns in the graph."""
        graph = await self.build_and_analyze(case_id)
        if not graph.nodes:
            return []

        patterns_found: list[dict[str, Any]] = []

        # Pattern: Multi-case identifier
        for node in graph.nodes:
            if len(node.cases) >= SUSPICIOUS_PATTERNS["multi_case"]["min_cases"]:
                patterns_found.append({
                    "pattern": "MULTI_CASE_IDENTIFIER",
                    "description": SUSPICIOUS_PATTERNS["multi_case"]["description"],
                    "entity_id": node.id,
                    "label": node.label,
                    "entity_type": node.entity_type,
                    "case_count": len(node.cases),
                    "cases": node.cases,
                })

        # Pattern: High degree (fan-out / fan-in)
        if graph.nodes:
            avg_degree = sum(n.degree for n in graph.nodes) / len(graph.nodes)
            for node in graph.nodes:
                if node.degree >= SUSPICIOUS_PATTERNS["fan_out"]["min_recipients"]:
                    patterns_found.append({
                        "pattern": "FAN_OUT",
                        "description": SUSPICIOUS_PATTERNS["fan_out"]["description"],
                        "entity_id": node.id,
                        "label": node.label,
                        "entity_type": node.entity_type,
                        "degree": node.degree,
                    })

        # Pattern: Bridge entity (high betweenness)
        for node in graph.nodes:
            if node.betweenness > 50:  # normalized * 100 > 50
                patterns_found.append({
                    "pattern": "BRIDGE_ENTITY",
                    "description": SUSPICIOUS_PATTERNS["bridge"]["description"],
                    "entity_id": node.id,
                    "label": node.label,
                    "entity_type": node.entity_type,
                    "betweenness": node.betweenness,
                })

        return patterns_found
