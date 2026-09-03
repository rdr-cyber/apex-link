"""Role-based access control tests."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, _login_with_challenge


@pytest.mark.asyncio
async def test_investigator_can_create_case(client: AsyncClient, auth_token):
    response = await client.post(
        "/api/v1/cases",
        json={"title": "Investigator Case", "description": "Test"},
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_analyst_cannot_create_case(client: AsyncClient):
    """Analysts should not be able to create cases."""
    from app.core.security import hash_password
    from app.models.user import User, UserRole
    from tests.conftest import TestSessionLocal

    analyst = User(
        username="testanalyst",
        email="analyst@test.com",
        password_hash=hash_password("analystpass"),
        full_name="Test Analyst",
        role=UserRole.ANALYST,
        email_verified=True,
    )
    async with TestSessionLocal() as db_session:
        db_session.add(analyst)
        await db_session.commit()

    token = await _login_with_challenge(client, "testanalyst", "analystpass")

    response = await client.post(
        "/api/v1/cases",
        json={"title": "Should Fail", "description": "Test"},
        headers=auth_headers(token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_investigator_cannot_delete_case(client: AsyncClient, auth_token):
    # Create a case
    create = await client.post(
        "/api/v1/cases",
        json={"title": "Delete Test", "description": "Test"},
        headers=auth_headers(auth_token),
    )
    case_id = create.json()["id"]

    # Try to delete (investigator role)
    response = await client.delete(
        f"/api/v1/cases/{case_id}",
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_unauthenticated_cannot_list_cases(client: AsyncClient):
    response = await client.get("/api/v1/cases")
    assert response.status_code == 403
