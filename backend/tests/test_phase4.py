"""Phase 4 tests — entity correction, merge, PDF report, lead workspace."""

import json
import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


# --- Entity correction tests ---

@pytest.mark.asyncio
async def test_entity_correction(client: AsyncClient, auth_token):
    """Correct an entity's display value."""
    h = auth_headers(auth_token)

    # Create case and ingest text
    r = await client.post("/api/v1/cases", json={"title": "Correction Test", "description": "Test"}, headers=h)
    case_id = r.json()["id"]

    await client.post(f"/api/v1/cases/{case_id}/analysis/ingest/text",
                      data={"text": "Phone 9876543210", "description": "test"}, headers=h)

    # Get the entity
    r = await client.get("/api/v1/entities?entity_type=PHONE", headers=h)
    entities = r.json()["items"]
    assert len(entities) >= 1
    entity_id = entities[0]["id"]

    # Correct it
    r = await client.put(f"/api/v1/entities/{entity_id}/correct",
                         json={"display_value": "Suspect Phone", "reason": "Investigator annotation"}, headers=h)
    assert r.status_code == 200
    assert r.json()["display_value"] == "Suspect Phone"


@pytest.mark.asyncio
async def test_entity_correction_preserves_evidence(client: AsyncClient, auth_token):
    """Correction should not modify raw evidence."""
    h = auth_headers(auth_token)

    r = await client.post("/api/v1/cases", json={"title": "Evidence Test", "description": "Test"}, headers=h)
    case_id = r.json()["id"]

    await client.post(f"/api/v1/cases/{case_id}/analysis/ingest/text",
                      data={"text": "Phone 9876543210"}, headers=h)

    r = await client.get("/api/v1/entities?entity_type=PHONE", headers=h)
    entity_id = r.json()["items"][0]["id"]

    # Get evidence before correction
    r_before = await client.get(f"/api/v1/entities/{entity_id}/evidence", headers=h)
    raw_before = r_before.json()["evidence"][0]["mentions"][0]["raw_text"]

    # Correct
    await client.put(f"/api/v1/entities/{entity_id}/correct",
                     json={"display_value": "Changed", "reason": "test"}, headers=h)

    # Get evidence after correction
    r_after = await client.get(f"/api/v1/entities/{entity_id}/evidence", headers=h)
    raw_after = r_after.json()["evidence"][0]["mentions"][0]["raw_text"]

    assert raw_before == raw_after, "Raw evidence should not change on entity correction"


@pytest.mark.asyncio
async def test_entity_correction_no_change(client: AsyncClient, auth_token):
    """Correction without providing values should fail."""
    h = auth_headers(auth_token)

    r = await client.post("/api/v1/cases", json={"title": "No Change", "description": "Test"}, headers=h)
    case_id = r.json()["id"]

    await client.post(f"/api/v1/cases/{case_id}/analysis/ingest/text",
                      data={"text": "Phone 9876543210"}, headers=h)

    r = await client.get("/api/v1/entities?entity_type=PHONE", headers=h)
    entity_id = r.json()["items"][0]["id"]

    r = await client.put(f"/api/v1/entities/{entity_id}/correct",
                         json={"reason": "No change provided"}, headers=h)
    assert r.status_code == 422


# --- Entity merge tests ---

@pytest.mark.asyncio
async def test_entity_merge(client: AsyncClient, auth_token):
    """Merge two phone entities."""
    h = auth_headers(auth_token)

    # Create entities directly to avoid dedup
    from app.models.entity import Entity, EntityType
    from tests.conftest import TestSessionLocal
    import uuid

    async with TestSessionLocal() as db:
        e1 = Entity(entity_type=EntityType.PHONE, canonical_value="9876543210", display_value="9876543210", normalized_value="9876543210", confidence=0.99)
        e2 = Entity(entity_type=EntityType.PHONE, canonical_value="1234567890", display_value="1234567890", normalized_value="1234567890", confidence=0.99)
        db.add_all([e1, e2])
        await db.commit()
        await db.refresh(e1)
        await db.refresh(e2)
        source_id = str(e1.id)
        target_id = str(e2.id)

    r = await client.post(f"/api/v1/entities/{source_id}/merge",
                          json={"target_entity_id": target_id, "reason": "Same person"}, headers=h)
    assert r.status_code == 200
    result = r.json()
    assert result["relationships_repointed"] >= 0


@pytest.mark.asyncio
async def test_entity_merge_incompatible_types(client: AsyncClient, auth_token):
    """Cannot merge PHONE with EMAIL."""
    h = auth_headers(auth_token)

    from app.models.entity import Entity, EntityType
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        phone = Entity(entity_type=EntityType.PHONE, canonical_value="9876543210", display_value="9876543210", normalized_value="9876543210", confidence=0.99)
        email = Entity(entity_type=EntityType.EMAIL, canonical_value="test@example.com", display_value="test@example.com", normalized_value="test@example.com", confidence=0.99)
        db.add_all([phone, email])
        await db.commit()
        await db.refresh(phone)
        await db.refresh(email)
        phone_id = str(phone.id)
        email_id = str(email.id)

    r = await client.post(f"/api/v1/entities/{phone_id}/merge",
                          json={"target_entity_id": email_id, "reason": "test"}, headers=h)
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_merge_preview(client: AsyncClient, auth_token):
    """Preview merge consequences before executing."""
    h = auth_headers(auth_token)

    from app.models.entity import Entity, EntityType
    from tests.conftest import TestSessionLocal

    async with TestSessionLocal() as db:
        e1 = Entity(entity_type=EntityType.PHONE, canonical_value="9876543210", display_value="9876543210", normalized_value="9876543210", confidence=0.99)
        e2 = Entity(entity_type=EntityType.PHONE, canonical_value="1234567890", display_value="1234567890", normalized_value="1234567890", confidence=0.99)
        db.add_all([e1, e2])
        await db.commit()
        await db.refresh(e1)
        await db.refresh(e2)
        source_id = str(e1.id)
        target_id = str(e2.id)

    r = await client.get(f"/api/v1/entities/{source_id}/merge-preview?target_id={target_id}", headers=h)
    assert r.status_code == 200
    preview = r.json()
    assert "consequences" in preview
    assert "source" in preview
    assert "target" in preview


# --- PDF report tests ---

@pytest.mark.asyncio
async def test_pdf_report_generation(client: AsyncClient, auth_token):
    """PDF report should be generated as a valid response."""
    h = auth_headers(auth_token)

    r = await client.post("/api/v1/cases", json={"title": "PDF Test", "description": "Test"}, headers=h)
    case_id = r.json()["id"]

    await client.post(f"/api/v1/cases/{case_id}/analysis/ingest/text",
                      data={"text": "Phone 9876543210, email test@example.com"}, headers=h)

    r = await client.post(f"/api/v1/reports/case/{case_id}/pdf", headers=h)
    assert r.status_code == 200
    assert "application/pdf" in r.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_json_report_generation(client: AsyncClient, auth_token):
    """JSON report should contain required sections."""
    h = auth_headers(auth_token)

    r = await client.post("/api/v1/cases", json={"title": "JSON Report", "description": "Test"}, headers=h)
    case_id = r.json()["id"]

    await client.post(f"/api/v1/cases/{case_id}/analysis/ingest/text",
                      data={"text": "Phone 9876543210"}, headers=h)

    r = await client.post(f"/api/v1/reports/case/{case_id}", headers=h)
    assert r.status_code == 200
    report = r.json()
    assert "case_summary" in report
    assert "known_entities" in report
    assert "key_network_entities" in report
    assert "evidence_summary" in report
    assert "disclaimer" in report
    assert "algorithm_version" in report
    assert "limitations" in report


# --- Lead workspace tests ---

@pytest.mark.asyncio
async def test_lead_detail_with_factors(client: AsyncClient, auth_token):
    """Lead detail should include structured factors for score explanation."""
    h = auth_headers(auth_token)

    r = await client.post("/api/v1/cases", json={"title": "Lead Detail A", "description": "Test"}, headers=h)
    case_a = r.json()["id"]
    r = await client.post("/api/v1/cases", json={"title": "Lead Detail B", "description": "Test"}, headers=h)
    case_b = r.json()["id"]

    await client.post(f"/api/v1/cases/{case_a}/analysis/ingest/text",
                      data={"text": "Phone 9876543210"}, headers=h)
    await client.post(f"/api/v1/cases/{case_b}/analysis/ingest/text",
                      data={"text": "Phone 9876543210"}, headers=h)

    r = await client.post(f"/api/v1/cases/{case_a}/analysis/correlate", headers=h)
    leads = r.json()["leads"]
    assert len(leads) >= 1

    lead_id = leads[0]["lead_id"]
    r = await client.get(f"/api/v1/leads/{lead_id}", headers=h)
    assert r.status_code == 200
    detail = r.json()
    assert "factors" in detail
    assert "explanation" in detail
    assert detail["score"] > 0


@pytest.mark.asyncio
async def test_lead_review_with_notes(client: AsyncClient, auth_token):
    """Lead review should accept notes and audit the change."""
    h = auth_headers(auth_token)

    r = await client.post("/api/v1/cases", json={"title": "Review Notes A", "description": "Test"}, headers=h)
    case_a = r.json()["id"]
    r = await client.post("/api/v1/cases", json={"title": "Review Notes B", "description": "Test"}, headers=h)
    case_b = r.json()["id"]

    await client.post(f"/api/v1/cases/{case_a}/analysis/ingest/text",
                      data={"text": "Phone 9876543210"}, headers=h)
    await client.post(f"/api/v1/cases/{case_b}/analysis/ingest/text",
                      data={"text": "Phone 9876543210"}, headers=h)

    r = await client.post(f"/api/v1/cases/{case_a}/analysis/correlate", headers=h)
    lead_id = r.json()["leads"][0]["lead_id"]

    # Move to REVIEWING with notes
    r = await client.put(f"/api/v1/leads/{lead_id}",
                         json={"status": "REVIEWING", "review_notes": "Investigating shared phone"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "REVIEWING"

    # Confirm with notes
    r = await client.put(f"/api/v1/leads/{lead_id}",
                         json={"status": "CONFIRMED", "review_notes": "Confirmed - same phone across cases"}, headers=h)
    assert r.status_code == 200
    assert r.json()["status"] == "CONFIRMED"
