"""Tests for High-Impact Intelligence Features:
- Network Path Finder
- Explain Connection
- Cross-Case Timeline
"""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, _login_with_challenge, TestSessionLocal
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.models.case import Case, CaseStatus, CasePriority
from app.models.entity import Entity, EntityType, CaseEntity
from app.models.evidence import Evidence, EvidenceType
from app.models.relationship import Relationship, RelationshipType


async def _setup_cases_with_shared_entities(client, db_session=None):
    """Create two cases with shared entities for testing.

    CASE-A: Person-A, Phone-X, UPI-X
    CASE-B: Person-B, Phone-X, UPI-X, Email-X

    Phone-X and UPI-X are shared → should produce a path.
    """
    async with TestSessionLocal() as session:
        # Get or create test user
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

        # Create Case A
        case_a = Case(
            case_number="AL-TEST-001", title="Test Case A",
            description="Path test case A", category="CYBER_FRAUD",
            priority=CasePriority.HIGH, status=CaseStatus.OPEN,
            created_by=user_id,
        )
        session.add(case_a)
        await session.flush()

        # Create Case B
        case_b = Case(
            case_number="AL-TEST-002", title="Test Case B",
            description="Path test case B", category="WIRE_FRAUD",
            priority=CasePriority.MEDIUM, status=CaseStatus.OPEN,
            created_by=user_id,
        )
        session.add(case_b)
        await session.flush()

        # Create entities
        person_a = Entity(
            entity_type=EntityType.PERSON, canonical_value="Person A",
            display_value="Person A", normalized_value="person a", confidence=0.95,
        )
        person_b = Entity(
            entity_type=EntityType.PERSON, canonical_value="Person B",
            display_value="Person B", normalized_value="person b", confidence=0.95,
        )
        phone_x = Entity(
            entity_type=EntityType.PHONE, canonical_value="9876543210",
            display_value="9876543210", normalized_value="9876543210", confidence=0.98,
        )
        upi_x = Entity(
            entity_type=EntityType.UPI_ID, canonical_value="demo@ybl",
            display_value="demo@ybl", normalized_value="demo@ybl", confidence=0.99,
        )
        email_x = Entity(
            entity_type=EntityType.EMAIL, canonical_value="demo@test.com",
            display_value="demo@test.com", normalized_value="demo@test.com", confidence=0.97,
        )

        for e in [person_a, person_b, phone_x, upi_x, email_x]:
            session.add(e)
        await session.flush()

        # Link entities to cases
        for eid in [person_a.id, phone_x.id, upi_x.id]:
            session.add(CaseEntity(case_id=case_a.id, entity_id=eid, confidence=0.9))
        for eid in [person_b.id, phone_x.id, upi_x.id, email_x.id]:
            session.add(CaseEntity(case_id=case_b.id, entity_id=eid, confidence=0.9))
        await session.flush()

        # Create relationships (Person-A → Phone-X → UPI-X → Person-B)
        rels = [
            (person_a.id, phone_x.id, RelationshipType.USES_PHONE, 0.95),
            (phone_x.id, upi_x.id, RelationshipType.MENTIONED_WITH, 0.90),
            (upi_x.id, person_b.id, RelationshipType.USES_UPI, 0.88),
            (person_b.id, email_x.id, RelationshipType.USES_EMAIL, 0.92),
        ]
        for src, tgt, rtype, conf in rels:
            session.add(Relationship(
                source_entity_id=src, target_entity_id=tgt,
                relationship_type=rtype, confidence=conf,
                case_id=case_a.id, description="test",
            ))
        await session.commit()

        return {
            "case_a_id": str(case_a.id),
            "case_b_id": str(case_b.id),
            "person_a_id": str(person_a.id),
            "person_b_id": str(person_b.id),
            "phone_x_id": str(phone_x.id),
            "upi_x_id": str(upi_x.id),
            "email_x_id": str(email_x.id),
        }


# ─── Path Finder Tests ───

@pytest.mark.asyncio
async def test_path_finder_case_to_case(client: AsyncClient, test_user):
    """Find path between two cases sharing entities."""
    ids = await _setup_cases_with_shared_entities(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/path", headers=h, json={
        "source_type": "CASE", "source_id": ids["case_a_id"],
        "target_type": "CASE", "target_id": ids["case_b_id"],
    })
    assert r.status_code == 200
    data = r.json()
    assert data.get("path_found") is True
    assert data["hop_count"] >= 1
    assert data["path_quality"] > 0
    assert len(data["path"]) >= 2
    assert "explanation" in data


@pytest.mark.asyncio
async def test_path_finder_entity_to_entity(client: AsyncClient, test_user):
    """Find path between two entities."""
    ids = await _setup_cases_with_shared_entities(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/path", headers=h, json={
        "source_type": "ENTITY", "source_id": ids["person_a_id"],
        "target_type": "ENTITY", "target_id": ids["person_b_id"],
    })
    assert r.status_code == 200
    data = r.json()
    assert data.get("path_found") is True
    assert data["hop_count"] >= 2


@pytest.mark.asyncio
async def test_path_finder_no_path(client: AsyncClient, test_user):
    """No path between disconnected entities."""
    ids = await _setup_cases_with_shared_entities(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/path", headers=h, json={
        "source_type": "ENTITY", "source_id": ids["person_a_id"],
        "target_type": "ENTITY", "source_id": ids["email_x_id"],
    })
    assert r.status_code in (200, 400)


@pytest.mark.asyncio
async def test_path_finder_invalid_types(client: AsyncClient, test_user):
    """Invalid source_type should be rejected."""
    ids = await _setup_cases_with_shared_entities(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/path", headers=h, json={
        "source_type": "INVALID", "source_id": ids["case_a_id"],
        "target_type": "CASE", "target_id": ids["case_b_id"],
    })
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_path_finder_cases_for_selection(client: AsyncClient, test_user):
    """List cases available for path selection."""
    ids = await _setup_cases_with_shared_entities(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.get("/api/v1/intelligence/cases-for-path", headers=h)
    assert r.status_code == 200
    cases = r.json()
    assert isinstance(cases, list)
    assert len(cases) >= 2


@pytest.mark.asyncio
async def test_path_finder_unauthorized(client: AsyncClient, test_user):
    """Unauthenticated user cannot use path finder."""
    r = await client.post("/api/v1/intelligence/path", json={
        "source_type": "CASE", "source_id": "00000000-0000-0000-0000-000000000001",
        "target_type": "CASE", "target_id": "00000000-0000-0000-0000-000000000002",
    })
    assert r.status_code == 403


# ─── Explain Connection Tests ───

@pytest.mark.asyncio
async def test_explain_connection(client: AsyncClient, test_user):
    """Explain why two connected cases are related."""
    ids = await _setup_cases_with_shared_entities(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/explain-connection", headers=h, json={
        "case_id": ids["case_a_id"],
        "related_case_id": ids["case_b_id"],
    })
    assert r.status_code == 200
    data = r.json()
    assert data["score"] > 0
    assert len(data["factors"]) > 0
    assert "explanation" in data
    assert "interpretation" in data

    # Verify factor structure
    for f in data["factors"]:
        assert "factor_type" in f
        assert "description" in f
        assert "observed_value" in f
        assert "weight" in f


@pytest.mark.asyncio
async def test_explain_connection_shared_entities_detected(client: AsyncClient, test_user):
    """Explanation should detect shared PHONE and UPI entities."""
    ids = await _setup_cases_with_shared_entities(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/explain-connection", headers=h, json={
        "case_id": ids["case_a_id"],
        "related_case_id": ids["case_b_id"],
    })
    data = r.json()
    factor_types = [f["factor_type"] for f in data["factors"]]
    assert "SHARED_PHONE" in factor_types
    assert "SHARED_UPI" in factor_types


@pytest.mark.asyncio
async def test_explain_connection_unauthorized(client: AsyncClient, test_user):
    """Unauthenticated user cannot explain connections."""
    r = await client.post("/api/v1/intelligence/explain-connection", json={
        "case_id": "00000000-0000-0000-0000-000000000001",
        "related_case_id": "00000000-0000-0000-0000-000000000002",
    })
    assert r.status_code == 403


# ─── Cross-Case Timeline Tests ───

@pytest.mark.asyncio
async def test_cross_case_timeline(client: AsyncClient, test_user):
    """Timeline should merge events from both cases."""
    ids = await _setup_cases_with_shared_entities(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/cross-case-timeline", headers=h, json={
        "case_ids": [ids["case_a_id"], ids["case_b_id"]],
    })
    assert r.status_code == 200
    data = r.json()
    assert "events" in data
    assert "total" in data
    assert data["total"] > 0
    assert "observations" in data


@pytest.mark.asyncio
async def test_cross_case_timeline_preserves_case_labels(client: AsyncClient, test_user):
    """Each event should be labeled with its case number."""
    ids = await _setup_cases_with_shared_entities(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/cross-case-timeline", headers=h, json={
        "case_ids": [ids["case_a_id"], ids["case_b_id"]],
    })
    data = r.json()
    case_numbers = set(e.get("case_number") for e in data["events"])
    assert "AL-TEST-001" in case_numbers
    assert "AL-TEST-002" in case_numbers


@pytest.mark.asyncio
async def test_cross_case_timeline_min_two_cases(client: AsyncClient, test_user):
    """Must require at least 2 cases."""
    ids = await _setup_cases_with_shared_entities(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/cross-case-timeline", headers=h, json={
        "case_ids": [ids["case_a_id"]],
    })
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_cross_case_timeline_sorted_chronologically(client: AsyncClient, test_user):
    """Events should be sorted by timestamp (oldest first)."""
    ids = await _setup_cases_with_shared_entities(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/cross-case-timeline", headers=h, json={
        "case_ids": [ids["case_a_id"], ids["case_b_id"]],
    })
    data = r.json()
    timestamps = [e.get("timestamp", "") for e in data["events"]]
    assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_cross_case_timeline_unauthorized(client: AsyncClient, test_user):
    """Unauthenticated user cannot access timeline."""
    r = await client.post("/api/v1/intelligence/cross-case-timeline", json={
        "case_ids": ["00000000-0000-0000-0000-000000000001", "00000000-0000-0000-0000-000000000002"],
    })
    assert r.status_code == 403


@pytest.mark.asyncio
async def test_cross_case_timeline_event_type_filter(client: AsyncClient, test_user):
    """Timeline should filter by event_type."""
    ids = await _setup_cases_with_shared_entities(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/cross-case-timeline", headers=h, json={
        "case_ids": [ids["case_a_id"], ids["case_b_id"]],
        "event_type": "ENTITY_LINKED",
    })
    assert r.status_code == 200
    data = r.json()
    for e in data["events"]:
        assert e["event_type"] == "ENTITY_LINKED"


# ─── Negative Tests ───

@pytest.mark.asyncio
async def test_same_entity_type_alone_not_strong(client: AsyncClient, test_user):
    """Shared entity types alone should not produce very high scores."""
    ids = await _setup_cases_with_shared_entities(client)
    token = await _login_with_challenge(client, "testuser", "testpass123")
    h = auth_headers(token)

    r = await client.post("/api/v1/intelligence/explain-connection", headers=h, json={
        "case_id": ids["case_a_id"],
        "related_case_id": ids["case_b_id"],
    })
    data = r.json()
    # With 2 shared types (PHONE + UPI), score should be moderate
    assert 20 <= data["score"] <= 80
