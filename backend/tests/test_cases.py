"""Case CRUD tests."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_create_case(client: AsyncClient, auth_token):
    response = await client.post(
        "/api/v1/cases",
        json={
            "title": "Test Case",
            "description": "Test description",
            "category": "CYBER_FRAUD",
            "priority": "HIGH",
            "location": "Mumbai",
        },
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Case"
    assert data["case_number"].startswith("AL-")
    assert data["priority"] == "HIGH"


@pytest.mark.asyncio
async def test_list_cases(client: AsyncClient, auth_token):
    # Create a case first
    await client.post(
        "/api/v1/cases",
        json={"title": "List Test Case", "description": "Test"},
        headers=auth_headers(auth_token),
    )

    response = await client.get(
        "/api/v1/cases",
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_get_case(client: AsyncClient, auth_token):
    create_response = await client.post(
        "/api/v1/cases",
        json={"title": "Get Test Case", "description": "Test"},
        headers=auth_headers(auth_token),
    )
    case_id = create_response.json()["id"]

    response = await client.get(
        f"/api/v1/cases/{case_id}",
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 200
    assert response.json()["title"] == "Get Test Case"


@pytest.mark.asyncio
async def test_update_case(client: AsyncClient, auth_token):
    create_response = await client.post(
        "/api/v1/cases",
        json={"title": "Update Test Case", "description": "Original"},
        headers=auth_headers(auth_token),
    )
    case_id = create_response.json()["id"]

    response = await client.put(
        f"/api/v1/cases/{case_id}",
        json={"title": "Updated Case", "priority": "CRITICAL"},
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Case"
    assert data["priority"] == "CRITICAL"


@pytest.mark.asyncio
async def test_delete_case_admin_only(client: AsyncClient, auth_token, admin_token):
    # Create a case
    create_response = await client.post(
        "/api/v1/cases",
        json={"title": "Delete Test Case", "description": "Test"},
        headers=auth_headers(auth_token),
    )
    case_id = create_response.json()["id"]

    # Investigator cannot delete
    response = await client.delete(
        f"/api/v1/cases/{case_id}",
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 403

    # Admin can delete
    response = await client.delete(
        f"/api/v1/cases/{case_id}",
        headers=auth_headers(admin_token),
    )
    assert response.status_code == 204


@pytest.mark.asyncio
async def test_search_cases(client: AsyncClient, auth_token):
    await client.post(
        "/api/v1/cases",
        json={"title": "Searchable Case XYZ", "description": "Unique text"},
        headers=auth_headers(auth_token),
    )

    response = await client.get(
        "/api/v1/cases?query=Searchable",
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
