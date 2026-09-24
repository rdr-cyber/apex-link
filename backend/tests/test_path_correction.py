"""Tests for path correction and score transparency.

Key scenario:
- CASE-A has ENTITY-A1 (connected to ENTITY-X), ENTITY-A2 (connected to HIGH-DEGREE)
- CASE-B has ENTITY-B1 (connected to ENTITY-X), ENTITY-B2
- HIGH-DEGREE has many connections but is NOT on the correct A→B path
- Path finder must discover A1→X→B1, not route through HIGH-DEGREE
"""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, _login_with_challenge, TestSessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.case import Case, CaseStatus, CasePriority
from app.models.entity import Entity, EntityType, CaseEntity
from app.models.relationship import Relationship, RelationshipType


async def _setup_multi_entity_dataset(client):
    """Create the test dataset proving multi-entity search works.

    CASE-A: ENTITY-A1, ENTITY-A2 (high-degree), ENTITY-A3
    CASE-B: ENTITY-B1, ENTITY-B2

    Network:
      ENTITY-A1 ─ ENTITY-X ─ ENTITY-B1    (correct route)
      ENTITY-A2 ─ ENTITY-HIGH ─ ENTITY-Z  (high-degree cluster, NOT the route)
      ENTITY-HIGH ─ ENTITY-W
      ENTITY-HIGH ─ ENTITY-V
      ENTITY-HIGH ─ ENTITY-U
      ENTITY-HIGH ─ ENTITY-T
    """
    async with TestSessionLocal() as session:
        from sqlalchemy import select
        result = await session.execute(select(User).where(User.username == "testuser"))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                username="testuser", email="test@test.com",
                password_hash=hash_password("testpass123"),
                full_name="Test User", role=UserRole.INVESTIGATOR,
                email_verified=True,
            )
            session.add(user)
            await session.flush()

        user_id = user.id

        # Cases
        case_a = Case(
            case_number="AL-PATH-001", title="Path Test A",
            description="Test case A", category="CYBER_FRAUD",
            priority=CasePriority.HIGH, status=CaseStatus.OPEN,
            created_by=user_id,
        )
        case_b = Case(
            case_number="AL-PATH-002", title="Path Test B",
            description="Test case B", category="WIRE_FRAUD",
            priority=CasePriority.MEDIUM, status=CaseStatus.OPEN,
            created_by=user_id,
        )
        session.add_all([case_a, case_b])
        await session.flush()

        # Entities
        entity_a1 = Entity(entity_type=EntityType.PERSON, canonical_value="Person A1",
            display_value="Person A1", normalized_value="person a1", confidence=0.95)
        entity_a2 = Entity(entity_type=EntityType.PERSON, canonical_value="Person A2",
            display_value="Person A2", normalized_value="person a2", confidence=0.95)
        entity_a3 = Entity(entity_type=EntityType.PHONE, canonical_value="1111111111",
            display_value="1111111111", normalized_value="1111111111", confidence=0.98)
        entity_x = Entity(entity_type=EntityType.UPI_ID, canonical_value="shared@upi",
            display_value="shared@upi", normalized_value="shared@upi", confidence=0.99)
        entity_b1 = Entity(entity_type=EntityType.PERSON, canonical_value="Person B1",
            display_value="Person B1", normalized_value="person b1", confidence=0.95)
        entity_b2 = Entity(entity_type=EntityType.EMAIL, canonical_value="b2@test.com",
            display_value="b2@test.com", normalized_value="b2@test.com", confidence=0.97)
        entity_high = Entity(entity_type=EntityType.PHONE, canonical_value="9999999999",
            display_value="9999999999", normalized_value="9999999999", confidence=0.98)
        entity_z = Entity(entity_type=EntityType.EMAIL, canonical_value="z@test.com",
            display_value="z@test.com", normalized_value="z@test.com", confidence=0.9)
        entity_w = Entity(entity_type=EntityType.EMAIL, canonical_value="w@test.com",
            display_value="w@test.com", normalized_value="w@test.com", confidence=0.9)
        entity_v = Entity(entity_type=EntityType.EMAIL, canonical_value="v@test.com",
            display_value="v@test.com", normalized_value="v@test.com", confidence=0.9)
        entity_u = Entity(entity_type=EntityType.EMAIL, canonical_value="u@test.com",
            display_value="u@test.com", normalized_value="u@test.com", confidence=0.9)
        entity_t = Entity(entity_type=EntityType.EMAIL, canonical_value="t@test.com",
            display_value="t@test.com", normalized_value="t@test.com", confidence=0.9)

        for e in [entity_a1, entity_a2, entity_a3, entity_x, entity_b1, entity_b2,
                  entity_high, entity_z, entity_w, entity_v, entity_u, entity_t]:
            session.add(e)
        await session.flush()

        # Case-entity links
        # CASE-A: A1, A2, A3
        for eid in [entity_a1.id, entity_a2.id, entity_a3.id]:
            session.add(CaseEntity(case_id=case_a.id, entity_id=eid, confidence=0.9))
        # CASE-B: B1, B2
        for eid in [entity_b1.id, entity_b2.id]:
            session.add(CaseEntity(case_id=case_b.id, entity_id=eid, confidence=0.9))
        await session.flush()

        # Relationships
        # Correct route: A1 → X → B1
        rels_correct = [
            (entity_a1.id, entity_x.id, RelationshipType.USES_UPI, 0.95),
            (entity_x.id, entity_b1.id, RelationshipType.USES_UPI, 0.92),
        ]
        # High-degree cluster (NOT the route): A2 → HIGH → Z, W, V, U, T
        rels_high = [
            (entity_a2.id, entity_high.id, RelationshipType.USES_PHONE, 0.90),
            (entity_high.id, entity_z.id, RelationshipType.MENTIONED_WITH, 0.85),
            (entity_high.id, entity_w.id, RelationshipType.MENTIONED_WITH, 0.85),
            (entity_high.id, entity_v.id, RelationshipType.MENTIONED_WITH, 0.85),
            (entity_high.id, entity_u.id, RelationshipType.MENTIONED_WITH, 0.85),
            (entity_high.id, entity_t.id, RelationshipType.MENTIONED_WITH, 0.85),
        ]
        # A3 has no connections to B
        for src, tgt, rtype, conf in rels_correct + rels_high:
            session.add(Relationship(
                source_entity_id=src, target_entity_id=tgt,
                relationship_type=rtype, confidence=conf,
                case_id=case_a.id, description="test",
            ))
        await session.commit()

        # Verify: HIGH-DEGREE has 6 connections, A1 has 1, X has 2
        return {
            "case_a_id": str(case_a.id),
            "case_b_id": str(case_b.id),
            "entity_a1_id": str(entity_a1.id),
            "entity_a2_id": str(entity_a2.id),
            "entity_x_id": str(entity_x.id),
            "entity_b1_id": str(entity_b1.id),
            "entity_high_id": str(entity_high.id),
        }


# ─── Multi-Entity Path Tests ───

@pytest.mark.asyncio
async def test_multi_entity_finds_correct_path(client: AsyncClient, test_user):
    """Path finder discovers A1→X→B1, NOT through HIGH-DEGREE entity."""
    ids = await _setup_multi_entity_dataset(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/path", headers=h, json={
        "source_type": "CASE", "source_id": ids["case_a_id"],
        "target_type": "CASE", "target_id": ids["case_b_id"],
    })
    assert r.status_code == 200
    data = r.json()
    assert data["path_found"] is True

    # The path should go through ENTITY-X, not ENTITY-HIGH
    node_ids = [n["node_id"] for n in data["path"]]
    assert ids["entity_x_id"] in node_ids, f"Path should include ENTITY-X but got: {node_ids}"
    assert ids["entity_high_id"] not in node_ids, f"Path should NOT include HIGH-DEGREE but got: {node_ids}"

    # Should report multi-entity search
    assert data.get("source_entities_searched", 0) >= 2
    assert data.get("target_entities_searched", 0) >= 1
    assert data.get("candidate_paths_found", 0) >= 1


@pytest.mark.asyncio
async def test_multi_entity_path_ranking(client: AsyncClient, test_user):
    """Path should include ranking factors."""
    ids = await _setup_multi_entity_dataset(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/path", headers=h, json={
        "source_type": "CASE", "source_id": ids["case_a_id"],
        "target_type": "CASE", "target_id": ids["case_b_id"],
    })
    data = r.json()
    assert "ranking" in data
    assert "rank_score" in data["ranking"]
    assert "evidence_count" in data["ranking"]
    assert "avg_confidence" in data["ranking"]
    assert "hops" in data["ranking"]


@pytest.mark.asyncio
async def test_entity_to_entity_path(client: AsyncClient, test_user):
    """Direct entity-to-entity path should still work."""
    ids = await _setup_multi_entity_dataset(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/path", headers=h, json={
        "source_type": "ENTITY", "source_id": ids["entity_a1_id"],
        "target_type": "ENTITY", "target_id": ids["entity_b1_id"],
    })
    assert r.status_code == 200
    data = r.json()
    assert data["path_found"] is True
    node_ids = [n["node_id"] for n in data["path"]]
    assert ids["entity_x_id"] in node_ids


@pytest.mark.asyncio
async def test_no_path_between_disconnected_cases(client: AsyncClient, test_user):
    """Cases with no shared entities should return no path."""
    ids = await _setup_multi_entity_dataset(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    # Create an isolated case
    async with TestSessionLocal() as session:
        from sqlalchemy import select
        user = (await session.execute(select(User).where(User.username == "testuser"))).scalar_one()
        case_c = Case(
            case_number="AL-PATH-003", title="Isolated",
            description="Isolated case", category="OTHER",
            priority=CasePriority.LOW, status=CaseStatus.OPEN,
            created_by=user.id,
        )
        session.add(case_c)
        await session.flush()
        iso_entity = Entity(entity_type=EntityType.PERSON, canonical_value="Isolated Person",
            display_value="Isolated Person", normalized_value="isolated person", confidence=0.9)
        session.add(iso_entity)
        await session.flush()
        session.add(CaseEntity(case_id=case_c.id, entity_id=iso_entity.id, confidence=0.9))
        await session.commit()
        case_c_id = str(case_c.id)

    r = await client.post("/api/v1/intelligence/path", headers=h, json={
        "source_type": "CASE", "source_id": ids["case_a_id"],
        "target_type": "CASE", "target_id": case_c_id,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["path_found"] is False
    assert "message" in data


@pytest.mark.asyncio
async def test_path_unauthorized_source(client: AsyncClient, test_user):
    """Unauthorized source should be rejected."""
    ids = await _setup_multi_entity_dataset(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/path", headers=h, json={
        "source_type": "CASE", "source_id": "00000000-0000-0000-0000-000000000001",
        "target_type": "CASE", "target_id": ids["case_b_id"],
    })
    assert r.status_code in (403, 404)


# ─── Score Transparency Tests ───

@pytest.mark.asyncio
async def test_explain_connection_score_transparency(client: AsyncClient, test_user):
    """Explain connection should return raw_score, normalized_score, normalization_method."""
    ids = await _setup_multi_entity_dataset(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/explain-connection", headers=h, json={
        "case_id": ids["case_a_id"],
        "related_case_id": ids["case_b_id"],
    })
    assert r.status_code == 200
    data = r.json()
    assert "raw_score" in data
    assert "normalized_score" in data
    assert "normalization_method" in data
    assert data["normalized_score"] == data["score"]  # score must equal normalized_score
    assert isinstance(data["raw_score"], (int, float))
    assert isinstance(data["normalized_score"], (int, float))


@pytest.mark.asyncio
async def test_explain_connection_factors_have_structure(client: AsyncClient, test_user):
    """Each factor should have the required structure."""
    ids = await _setup_multi_entity_dataset(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/explain-connection", headers=h, json={
        "case_id": ids["case_a_id"],
        "related_case_id": ids["case_b_id"],
    })
    data = r.json()
    for f in data["factors"]:
        assert "factor_type" in f
        assert "description" in f
        assert "observed_value" in f
        assert "weight" in f
        assert "confidence" in f


@pytest.mark.asyncio
async def test_score_does_not_exceed_100(client: AsyncClient, test_user):
    """Normalized score should never exceed 100."""
    ids = await _setup_multi_entity_dataset(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/explain-connection", headers=h, json={
        "case_id": ids["case_a_id"],
        "related_case_id": ids["case_b_id"],
    })
    data = r.json()
    assert data["normalized_score"] <= 100
    assert data["score"] <= 100
