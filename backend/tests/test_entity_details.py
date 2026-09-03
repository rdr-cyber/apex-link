"""Tests for entity detail API endpoints."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_entity_list_and_search(client: AsyncClient, auth_token):
    """Test entity listing with normalized search."""
    # Create a case and ingest text with entities
    r = await client.post("/api/v1/cases", json={"title": "Entity Test", "description": "Test"}, headers=auth_headers(auth_token))
    case_id = r.json()["id"]

    text = "Contact +91 98765 43210 or test@example.com. IP: 10.0.0.1"
    await client.post(f"/api/v1/cases/{case_id}/analysis/ingest/text", data={"text": text, "description": "test"}, headers=auth_headers(auth_token))

    # List entities
    r = await client.get("/api/v1/entities", headers=auth_headers(auth_token))
    assert r.status_code == 200
    assert r.json()["total"] >= 2

    # Search by phone with country code (should normalize)
    r = await client.get("/api/v1/entities?query=+91 98765 43210", headers=auth_headers(auth_token))
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    # Search by email case-insensitive
    r = await client.get("/api/v1/entities?query=TEST@EXAMPLE.COM", headers=auth_headers(auth_token))
    assert r.status_code == 200
    assert r.json()["total"] >= 1

    # Filter by entity type
    r = await client.get("/api/v1/entities?entity_type=PHONE", headers=auth_headers(auth_token))
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["entity_type"] == "PHONE"


@pytest.mark.asyncio
async def test_entity_detail_endpoints(client: AsyncClient, auth_token):
    """Test entity cases, evidence, relationships, timeline endpoints."""
    r = await client.post("/api/v1/cases", json={"title": "Detail Test", "description": "Test"}, headers=auth_headers(auth_token))
    case_id = r.json()["id"]

    text = "Contact Vikram at +91 98765 43210 or vikram@test.com"
    await client.post(f"/api/v1/cases/{case_id}/analysis/ingest/text", data={"text": text, "description": "test"}, headers=auth_headers(auth_token))
    await client.post(f"/api/v1/cases/{case_id}/analysis/run", headers=auth_headers(auth_token))

    # Get an entity ID
    r = await client.get("/api/v1/entities?entity_type=PHONE", headers=auth_headers(auth_token))
    entity_id = r.json()["items"][0]["id"]

    # Get entity cases
    r = await client.get(f"/api/v1/entities/{entity_id}/cases", headers=auth_headers(auth_token))
    assert r.status_code == 200
    assert r.json()["total_cases"] >= 1

    # Get entity evidence
    r = await client.get(f"/api/v1/entities/{entity_id}/evidence", headers=auth_headers(auth_token))
    assert r.status_code == 200
    assert r.json()["evidence_count"] >= 1

    # Get entity relationships
    r = await client.get(f"/api/v1/entities/{entity_id}/relationships", headers=auth_headers(auth_token))
    assert r.status_code == 200
    assert r.json()["relationship_count"] >= 1

    # Get entity timeline
    r = await client.get(f"/api/v1/entities/{entity_id}/timeline", headers=auth_headers(auth_token))
    assert r.status_code == 200
    assert r.json()["total"] >= 1


@pytest.mark.asyncio
async def test_entity_not_found(client: AsyncClient, auth_token):
    """Test 404 for non-existent entity."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = await client.get(f"/api/v1/entities/{fake_id}", headers=auth_headers(auth_token))
    assert r.status_code == 404

    r = await client.get(f"/api/v1/entities/{fake_id}/cases", headers=auth_headers(auth_token))
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_csv_ingestion(client: AsyncClient, auth_token):
    """Test CSV ingestion endpoint."""
    r = await client.post("/api/v1/cases", json={"title": "CSV Test", "description": "Test"}, headers=auth_headers(auth_token))
    case_id = r.json()["id"]

    # Create a CDR CSV
    csv_content = "timestamp,caller,receiver,duration_seconds,cell_id,location\n2026-01-15 09:00,+91 98765 43210,+91 87654 32109,120,CELL-001,Mumbai\n2026-01-15 09:05,+91 76543 21098,+91 65432 10987,60,CELL-002,Delhi"

    import io
    files = {"file": ("test.csv", csv_content.encode(), "text/csv")}
    data = {"csv_type": "auto"}

    r = await client.post(f"/api/v1/cases/{case_id}/ingest/csv", files=files, data=data, headers=auth_headers(auth_token))
    assert r.status_code == 200
    result = r.json()
    assert result["total_rows"] == 2
    assert result["successful_rows"] >= 1


@pytest.mark.asyncio
async def test_csv_invalid_type(client: AsyncClient, auth_token):
    """Test CSV with unrecognizable headers."""
    r = await client.post("/api/v1/cases", json={"title": "CSV Bad", "description": "Test"}, headers=auth_headers(auth_token))
    case_id = r.json()["id"]

    csv_content = "col_a,col_b,col_c\n1,2,3"
    files = {"file": ("bad.csv", csv_content.encode(), "text/csv")}
    data = {"csv_type": "auto"}

    r = await client.post(f"/api/v1/cases/{case_id}/ingest/csv", files=files, data=data, headers=auth_headers(auth_token))
    assert r.status_code == 422
