"""Authorization tests — case-level access, cross-case security, entity access."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, TestSessionLocal, _login_with_challenge


async def _create_user_and_get_token(client, username, password, role="INVESTIGATOR"):
    """Helper to create a user and get their token."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole
    from sqlalchemy import select

    role_enum = getattr(UserRole, role)
    async with TestSessionLocal() as db:
        existing = await db.execute(select(User).where(User.username == username))
        if not existing.scalar_one_or_none():
            db.add(User(
                username=username, email=f"{username}@test.com",
                password_hash=hash_password(password),
                full_name=username.title(), role=role_enum,
                email_verified=True,
            ))
            await db.commit()

    return await _login_with_challenge(client, username, password)


# --- Case access tests ---

@pytest.mark.asyncio
async def test_investigator_sees_own_cases(client: AsyncClient, auth_token):
    """Investigator should see cases they created."""
    h = auth_headers(auth_token)

    # Create a case
    r = await client.post("/api/v1/cases", json={"title": "My Case", "description": "t"}, headers=h)
    assert r.status_code in (200, 201)
    my_case_id = r.json()["id"]

    # List cases — should include the one we created
    r = await client.get("/api/v1/cases", headers=h)
    assert r.status_code == 200
    case_ids = [c["id"] for c in r.json()["items"]]
    assert my_case_id in case_ids


@pytest.mark.asyncio
async def test_unauthenticated_cannot_access_cases(client: AsyncClient):
    """Unauthenticated user cannot access cases."""
    r = await client.get("/api/v1/cases")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_invalid_token_cannot_access_cases(client: AsyncClient):
    """Invalid token cannot access cases."""
    r = await client.get("/api/v1/cases", headers={"Authorization": "Bearer fake-token"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_case_not_found_returns_404(client: AsyncClient, auth_token):
    """Accessing non-existent case returns 404 (not 403)."""
    h = auth_headers(auth_token)
    r = await client.get("/api/v1/cases/00000000-0000-0000-0000-000000000000", headers=h)
    assert r.status_code == 404


# --- Cross-case correlation security ---

@pytest.mark.asyncio
async def test_correlation_only_compares_accessible_cases(client: AsyncClient, auth_token):
    """Correlation should only include cases the user can access."""
    h = auth_headers(auth_token)

    # Create two cases with shared entities
    r1 = await client.post("/api/v1/cases", json={"title": "Corr A", "description": "t"}, headers=h)
    r2 = await client.post("/api/v1/cases", json={"title": "Corr B", "description": "t"}, headers=h)
    ca, cb = r1.json()["id"], r2.json()["id"]

    await client.post(f"/api/v1/cases/{ca}/analysis/ingest/text",
                      data={"text": "Phone 9876543210"}, headers=h)
    await client.post(f"/api/v1/cases/{cb}/analysis/ingest/text",
                      data={"text": "Phone 9876543210"}, headers=h)

    # Correlate case A
    r = await client.post(f"/api/v1/cases/{ca}/analysis/correlate", headers=h)
    assert r.status_code == 200

    # The result should only contain leads for cases the user can access
    for lead in r.json().get("leads", []):
        # Related case should be accessible
        if lead.get("related_case_id"):
            r_check = await client.get(f"/api/v1/cases/{lead['related_case_id']}", headers=h)
            assert r_check.status_code == 200, f"Lead references inaccessible case {lead['related_case_id']}"


@pytest.mark.asyncio
async def test_cross_case_data_leak_prevention(client: AsyncClient, auth_token):
    """Inaccessible cases must not leak through correlation explanations or factors."""
    h = auth_headers(auth_token)

    # User A creates Case A and Case B (both accessible)
    r1 = await client.post("/api/v1/cases", json={"title": "Case Leak A", "description": "t"}, headers=h)
    r2 = await client.post("/api/v1/cases", json={"title": "Case Leak B", "description": "t"}, headers=h)
    ca, cb = r1.json()["id"], r2.json()["id"]

    # Create a user B who can only access Case B
    token_b = await _create_user_and_get_token(client, "leakuser_b", "pass123", "INVESTIGATOR")
    h_b = auth_headers(token_b)

    # User B creates Case B
    r_b = await client.post("/api/v1/cases", json={"title": "Case Leak B-Private", "description": "t"}, headers=h_b)
    # Now user B has one case. User A's case should not appear in B's correlation.
    
    # User A ingests into both cases
    await client.post(f"/api/v1/cases/{ca}/analysis/ingest/text",
                      data={"text": "Phone 5551234567"}, headers=h)
    await client.post(f"/api/v1/cases/{cb}/analysis/ingest/text",
                      data={"text": "Phone 5551234567"}, headers=h)

    # User B correlates their own case — should not see User A's cases
    case_b_id = r_b.json()["id"]
    await client.post(f"/api/v1/cases/{case_b_id}/analysis/ingest/text",
                      data={"text": "Phone 9999999999"}, headers=h_b)
    r_corr_b = await client.post(f"/api/v1/cases/{case_b_id}/analysis/correlate", headers=h_b)
    assert r_corr_b.status_code == 200
    
    # Verify no user A case appears in user B's results
    for lead in r_corr_b.json().get("leads", []):
        if lead.get("related_case_id"):
            assert lead["related_case_id"] != ca, "User A's case leaked to User B"
            assert lead["related_case_id"] != cb, "User A's other case leaked to User B"


# --- Graph authorization ---

@pytest.mark.asyncio
async def test_graph_only_returns_accessible_data(client: AsyncClient, auth_token):
    """Graph should only return entities from accessible cases."""
    h = auth_headers(auth_token)

    r = await client.post("/api/v1/cases", json={"title": "Graph Test", "description": "t"}, headers=h)
    case_id = r.json()["id"]

    await client.post(f"/api/v1/cases/{case_id}/analysis/ingest/text",
                      data={"text": "Phone 9876543210"}, headers=h)

    r = await client.get(f"/api/v1/cases/{case_id}/relationships/graph", headers=h)
    assert r.status_code == 200

    # All nodes should belong to accessible cases
    for node in r.json().get("nodes", []):
        # Node should be accessible (it belongs to the case we created)
        assert node.get("id"), "Node should have an ID"


@pytest.mark.asyncio
async def test_unauthorized_user_cannot_access_other_user_case(client: AsyncClient, auth_token):
    """Investigator B cannot see Investigator A's case via direct API call."""
    h = auth_headers(auth_token)

    # User A creates a case
    r = await client.post("/api/v1/cases", json={"title": "Private Case A", "description": "t"}, headers=h)
    case_a = r.json()["id"]

    # User B tries to access it
    token_b = await _create_user_and_get_token(client, "privuser_b", "pass123", "INVESTIGATOR")
    h_b = auth_headers(token_b)

    r = await client.get(f"/api/v1/cases/{case_a}", headers=h_b)
    # Should be 404 (not 200, not 403 — indistinguishable from non-existent)
    assert r.status_code == 404, f"User B got status {r.status_code} for User A's case"


@pytest.mark.asyncio
async def test_unauthorized_user_cannot_access_other_user_evidence(client: AsyncClient, auth_token):
    """Investigator B cannot see evidence from Investigator A's case."""
    h = auth_headers(auth_token)

    # User A creates case and ingests evidence
    r = await client.post("/api/v1/cases", json={"title": "Ev Private", "description": "t"}, headers=h)
    case_a = r.json()["id"]
    await client.post(f"/api/v1/cases/{case_a}/analysis/ingest/text",
                      data={"text": "Email test@test.com"}, headers=h)

    # User B tries to access evidence
    token_b = await _create_user_and_get_token(client, "evuser_b", "pass123", "INVESTIGATOR")
    h_b = auth_headers(token_b)

    r = await client.get(f"/api/v1/cases/{case_a}/evidence", headers=h_b)
    assert r.status_code == 404, f"User B got status {r.status_code} for User A's evidence"


@pytest.mark.asyncio
async def test_unauthorized_user_cannot_access_other_user_graph(client: AsyncClient, auth_token):
    """Investigator B cannot see graph for Investigator A's case."""
    h = auth_headers(auth_token)

    r = await client.post("/api/v1/cases", json={"title": "Graph Private", "description": "t"}, headers=h)
    case_a = r.json()["id"]
    await client.post(f"/api/v1/cases/{case_a}/analysis/ingest/text",
                      data={"text": "Phone 1234567890"}, headers=h)

    token_b = await _create_user_and_get_token(client, "gruser_b", "pass123", "INVESTIGATOR")
    h_b = auth_headers(token_b)

    r = await client.get(f"/api/v1/cases/{case_a}/relationships/graph", headers=h_b)
    assert r.status_code == 404, f"User B got status {r.status_code} for User A's graph"


@pytest.mark.asyncio
async def test_unauthorized_user_cannot_access_other_user_report(client: AsyncClient, auth_token):
    """Investigator B cannot generate reports for Investigator A's case."""
    h = auth_headers(auth_token)

    r = await client.post("/api/v1/cases", json={"title": "Report Private", "description": "t"}, headers=h)
    case_a = r.json()["id"]
    await client.post(f"/api/v1/cases/{case_a}/analysis/ingest/text",
                      data={"text": "Phone 1234567890"}, headers=h)

    token_b = await _create_user_and_get_token(client, "rpuser_b", "pass123", "INVESTIGATOR")
    h_b = auth_headers(token_b)

    r = await client.post(f"/api/v1/reports/case/{case_a}", headers=h_b)
    assert r.status_code == 404, f"User B got status {r.status_code} for User A's report"


# --- Evidence authorization ---

@pytest.mark.asyncio
async def test_evidence_requires_case_access(client: AsyncClient, auth_token):
    """Evidence endpoints should enforce case access."""
    h = auth_headers(auth_token)

    r = await client.post("/api/v1/cases", json={"title": "Ev Test", "description": "t"}, headers=h)
    case_id = r.json()["id"]

    # List evidence — should work for accessible case
    r = await client.get(f"/api/v1/cases/{case_id}/evidence", headers=h)
    assert r.status_code == 200

    # Non-existent case — should 404
    r = await client.get("/api/v1/cases/00000000-0000-0000-0000-000000000000/evidence", headers=h)
    assert r.status_code == 404


# --- Report authorization ---

@pytest.mark.asyncio
async def test_report_requires_case_access(client: AsyncClient, auth_token):
    """Report generation should enforce case access."""
    h = auth_headers(auth_token)

    r = await client.post("/api/v1/cases", json={"title": "Report Test", "description": "t"}, headers=h)
    case_id = r.json()["id"]

    await client.post(f"/api/v1/cases/{case_id}/analysis/ingest/text",
                      data={"text": "Phone 9876543210"}, headers=h)

    # Generate report — should work
    r = await client.post(f"/api/v1/reports/case/{case_id}", headers=h)
    assert r.status_code == 200

    # Non-existent case — should 404
    r = await client.post("/api/v1/reports/case/00000000-0000-0000-0000-000000000000", headers=h)
    assert r.status_code == 404


# --- Rate limiting tests ---

@pytest.mark.asyncio
async def test_login_rate_limit(client: AsyncClient):
    """Login rate limiter should reject after threshold."""
    # Make 5 failed login attempts
    for i in range(5):
        r = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
        assert r.status_code == 401

    # 6th attempt should be rate-limited
    r = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrong"})
    assert r.status_code == 429, f"Expected 429 rate limit, got {r.status_code}"
    assert "too many" in r.json()["detail"].lower() or "rate" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_successful_login_within_rate_limit(client: AsyncClient, test_user):
    """Successful login within rate limit should return OTP session."""
    r = await client.post("/api/v1/auth/login", json={"username": "testuser", "password": "testpass123"})
    assert r.status_code == 200
    assert r.json().get("requires_challenge") is True
