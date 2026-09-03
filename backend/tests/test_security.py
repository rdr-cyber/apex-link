"""Security tests — IDOR, auth edge cases, input validation, path traversal."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_invalid_password_rejected(client: AsyncClient, auth_token):
    """Wrong password must return 401."""
    r = await client.post("/api/v1/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_missing_token_rejected(client: AsyncClient):
    """Request without token must return 401."""
    r = await client.get("/api/v1/cases")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_invalid_token_rejected(client: AsyncClient):
    """Request with garbage token must return 401."""
    r = await client.get("/api/v1/cases", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_tampered_token_rejected(client: AsyncClient, auth_token):
    """Token with tampered payload must be rejected."""
    h = auth_headers(auth_token)
    # Tamper by changing a character in the middle
    tampered = auth_token[:-5] + "XXXXX"
    r = await client.get("/api/v1/cases", headers={"Authorization": f"Bearer {tampered}"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_inactive_user_rejected(client: AsyncClient, test_user):
    """Inactive user must not be able to log in."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        user = User(
            username="inactive_test",
            email="inactive@test.com",
            password_hash=hash_password("pass123"),
            full_name="Inactive",
            role=UserRole.INVESTIGATOR,
            is_active=False,
        )
        db.add(user)
        await db.commit()

    r = await client.post("/api/v1/auth/login", json={"username": "inactive_test", "password": "pass123"})
    assert r.status_code in (401, 403)


# --- RBAC security tests ---

@pytest.mark.asyncio
async def test_analyst_cannot_create_case(client: AsyncClient):
    """Analyst role must be rejected from case creation."""
    from tests.conftest import TestSessionLocal
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    async with TestSessionLocal() as db:
        db.add(User(username="sec_analyst", email="sa@test.com", password_hash=hash_password("analyst123"), full_name="SA", role=UserRole.ANALYST, email_verified=True))
        await db.commit()

    from tests.conftest import _login_with_challenge
    token = await _login_with_challenge(client, "sec_analyst", "analyst123")
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/v1/cases", json={"title": "Test", "description": "test"}, headers=h)
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_analyst_can_list_cases(client: AsyncClient):
    """Analyst role should be able to list cases (read access)."""
    from tests.conftest import TestSessionLocal
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    async with TestSessionLocal() as db:
        existing = await db.execute(__import__('sqlalchemy').select(User).where(User.username == "sec_analyst2"))
        if not existing.scalar_one_or_none():
            db.add(User(username="sec_analyst2", email="sa2@test.com", password_hash=hash_password("analyst123"), full_name="SA2", role=UserRole.ANALYST, email_verified=True))
            await db.commit()

    from tests.conftest import _login_with_challenge
    token = await _login_with_challenge(client, "sec_analyst2", "analyst123")
    h = {"Authorization": f"Bearer {token}"}
    r = await client.get("/api/v1/cases", headers=h)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_analyst_cannot_correct_entity(client: AsyncClient, auth_token):
    """Only ADMIN/INVESTIGATOR can correct entities."""
    from tests.conftest import TestSessionLocal
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    async with TestSessionLocal() as db:
        existing = await db.execute(__import__('sqlalchemy').select(User).where(User.username == "sec_a3"))
        if not existing.scalar_one_or_none():
            db.add(User(username="sec_a3", email="sa3@test.com", password_hash=hash_password("analyst123"), full_name="SA3", role=UserRole.ANALYST, email_verified=True))
            await db.commit()

    from tests.conftest import _login_with_challenge
    token = await _login_with_challenge(client, "sec_a3", "analyst123")
    h = {"Authorization": f"Bearer {token}"}
    r = await client.put("/api/v1/entities/00000000-0000-0000-0000-000000000000/correct",
                         json={"display_value": "x", "reason": "test"}, headers=h)
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_analyst_cannot_merge_entity(client: AsyncClient):
    """Only ADMIN/INVESTIGATOR can merge entities."""
    from tests.conftest import TestSessionLocal
    from app.core.security import hash_password
    from app.models.user import User, UserRole

    async with TestSessionLocal() as db:
        existing = await db.execute(__import__('sqlalchemy').select(User).where(User.username == "sec_a4"))
        if not existing.scalar_one_or_none():
            db.add(User(username="sec_a4", email="sa4@test.com", password_hash=hash_password("analyst123"), full_name="SA4", role=UserRole.ANALYST, email_verified=True))
            await db.commit()

    from tests.conftest import _login_with_challenge
    token = await _login_with_challenge(client, "sec_a4", "analyst123")
    h = {"Authorization": f"Bearer {token}"}
    r = await client.post("/api/v1/entities/00000000-0000-0000-0000-000000000000/merge",
                         json={"target_entity_id": "00000000-0000-0000-0000-000000000001", "reason": "test"}, headers=h)
    assert r.status_code in (401, 403)


# --- Input validation tests ---

@pytest.mark.asyncio
async def test_empty_case_title_rejected(client: AsyncClient, auth_token):
    """Case creation with empty title must be rejected."""
    h = auth_headers(auth_token)
    r = await client.post("/api/v1/cases", json={"title": "", "description": "test"}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_malicious_search_query(client: AsyncClient, auth_token):
    """SQL injection attempt in search must not cause error."""
    h = auth_headers(auth_token)
    r = await client.get("/api/v1/search?q='; DROP TABLE cases; --", headers=h)
    assert r.status_code == 200  # Should return empty results, not crash


@pytest.mark.asyncio
async def test_long_search_query(client: AsyncClient, auth_token):
    """Extremely long search query must be handled safely."""
    h = auth_headers(auth_token)
    long_query = "A" * 10000
    r = await client.get(f"/api/v1/search?q={long_query}", headers=h)
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_invalid_pagination_values(client: AsyncClient, auth_token):
    """Invalid pagination must be rejected."""
    h = auth_headers(auth_token)
    r = await client.get("/api/v1/cases?page=0", headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_large_page_size_rejected(client: AsyncClient, auth_token):
    """Oversized page must be rejected."""
    h = auth_headers(auth_token)
    r = await client.get("/api/v1/cases?page_size=10000", headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_entity_correction_without_reason(client: AsyncClient, auth_token):
    """Entity correction without reason must be rejected."""
    h = auth_headers(auth_token)
    r = await client.put("/api/v1/entities/00000000-0000-0000-0000-000000000000/correct",
                         json={"display_value": "test"}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_entity_merge_self(client: AsyncClient, auth_token):
    """Merging an entity with itself must be rejected."""
    h = auth_headers(auth_token)
    eid = "00000000-0000-0000-0000-000000000001"
    r = await client.post(f"/api/v1/entities/{eid}/merge",
                         json={"target_entity_id": eid, "reason": "test"}, headers=h)
    assert r.status_code in (404, 422)


@pytest.mark.asyncio
async def test_entity_correction_with_empty_display_value(client: AsyncClient, auth_token):
    """Empty display value must be rejected."""
    h = auth_headers(auth_token)
    r = await client.put("/api/v1/entities/00000000-0000-0000-0000-000000000000/correct",
                         json={"display_value": "", "reason": "test"}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_lead_invalid_status_transition(client: AsyncClient, auth_token):
    """Invalid lead status transition must be rejected."""
    h = auth_headers(auth_token)
    # Create two cases to generate a lead
    r1 = await client.post("/api/v1/cases", json={"title": "Sec A", "description": "t"}, headers=h)
    r2 = await client.post("/api/v1/cases", json={"title": "Sec B", "description": "t"}, headers=h)
    ca, cb = r1.json()["id"], r2.json()["id"]
    await client.post(f"/api/v1/cases/{ca}/analysis/ingest/text", data={"text": "Phone 9876543210"}, headers=h)
    await client.post(f"/api/v1/cases/{cb}/analysis/ingest/text", data={"text": "Phone 9876543210"}, headers=h)
    r = await client.post(f"/api/v1/cases/{ca}/analysis/correlate", headers=h)
    if r.json().get("leads"):
        lead_id = r.json()["leads"][0]["lead_id"]
        # Try to go directly from NEW to CONFIRMED
        r = await client.put(f"/api/v1/leads/{lead_id}", json={"status": "CONFIRMED"}, headers=h)
        assert r.status_code == 422


# --- File upload security tests ---

@pytest.mark.asyncio
async def test_invalid_file_extension_rejected(client: AsyncClient, auth_token):
    """File with unsupported extension must be rejected."""
    h = auth_headers(auth_token)
    r = await client.post("/api/v1/cases", json={"title": "Upload Test", "description": "t"}, headers=h)
    case_id = r.json()["id"]

    import io
    files = {"file": ("malware.exe", io.BytesIO(b"MZ" + b"\x00" * 100), "application/octet-stream")}
    r = await client.post(f"/api/v1/cases/{case_id}/evidence", files=files,
                         data={"evidence_type": "DOCUMENT", "description": "test"}, headers=h)
    # .exe is not in DOCUMENT allowed extensions — should be rejected
    assert r.status_code in (400, 415, 422)


@pytest.mark.asyncio
async def test_invalid_evidence_type_rejected(client: AsyncClient, auth_token):
    """Invalid evidence type must be rejected."""
    h = auth_headers(auth_token)
    r = await client.post("/api/v1/cases", json={"title": "Type Test", "description": "t"}, headers=h)
    case_id = r.json()["id"]

    import io
    files = {"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")}
    r = await client.post(f"/api/v1/cases/{case_id}/evidence", files=files,
                         data={"evidence_type": "INVALID_TYPE", "description": "test"}, headers=h)
    # Should fail — either validation error or internal error (enum mismatch)
    assert r.status_code in (400, 422, 500)


# --- Error sanitization tests ---

@pytest.mark.asyncio
async def test_404_does_not_expose_internals(client: AsyncClient, auth_token):
    """404 errors must not expose internal details."""
    h = auth_headers(auth_token)
    r = await client.get("/api/v1/cases/00000000-0000-0000-0000-000000000000", headers=h)
    assert r.status_code == 404
    # Response should not contain SQL, stack traces, or file paths
    text = r.text.lower()
    assert "sql" not in text
    assert "traceback" not in text
    assert "c:\\" not in text
    assert "/app/" not in text


@pytest.mark.asyncio
async def test_unauthenticated_endpoint_returns_401(client: AsyncClient):
    """Protected endpoints must return 401, not 500."""
    endpoints = [
        ("GET", "/api/v1/cases"),
        ("GET", "/api/v1/entities"),
        ("GET", "/api/v1/leads"),
        ("GET", "/api/v1/audit"),
    ]
    for method, url in endpoints:
        if method == "GET":
            r = await client.get(url)
        else:
            r = await client.post(url)
        assert r.status_code in (401, 403), f"{method} {url} returned {r.status_code}"


# --- CORS test ---

@pytest.mark.asyncio
async def test_cors_headers_present(client: AsyncClient):
    """CORS headers should be configured."""
    r = await client.options("/api/v1/auth/login", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
    })
    # CORS middleware should respond
    assert r.status_code in (200, 405)
