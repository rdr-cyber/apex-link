"""Performance benchmarks for TRACE-NET graph analytics."""

import time
import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers


@pytest.mark.asyncio
async def test_graph_benchmark_small(client: AsyncClient, auth_token):
    """Benchmark graph with ~20 entities."""
    h = auth_headers(auth_token)

    r = await client.post("/api/v1/cases", json={"title": "Bench Small", "description": "perf"}, headers=h)
    case_id = r.json()["id"]

    # Ingest 15 texts with shared entities
    for i in range(15):
        text = f"Phone {1000000000+i} email user{i}@test.com IP 192.168.1.{i}"
        await client.post(f"/api/v1/cases/{case_id}/analysis/ingest/text",
                          data={"text": text}, headers=h)

    # Benchmark graph
    start = time.perf_counter()
    r = await client.get(f"/api/v1/cases/{case_id}/relationships/graph", headers=h)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert r.status_code == 200
    nodes = len(r.json().get("nodes", []))
    edges = len(r.json().get("edges", []))
    print(f"\n  Small graph: {nodes} nodes, {edges} edges, {elapsed_ms:.0f}ms")
    assert elapsed_ms < 5000, f"Graph took {elapsed_ms:.0f}ms — too slow"


@pytest.mark.asyncio
async def test_graph_benchmark_medium(client: AsyncClient, auth_token):
    """Benchmark graph with ~100 entities."""
    h = auth_headers(auth_token)

    r = await client.post("/api/v1/cases", json={"title": "Bench Med", "description": "perf"}, headers=h)
    case_id = r.json()["id"]

    # Create a second case with shared entities for cross-case
    r2 = await client.post("/api/v1/cases", json={"title": "Bench Med 2", "description": "perf"}, headers=h)
    case2_id = r2.json()["id"]

    # Ingest to both cases with some shared entities
    for i in range(30):
        text = f"Phone {1000000000+i} email user{i}@test.com IP 192.168.1.{i} UPI upi{i}@pay"
        await client.post(f"/api/v1/cases/{case_id}/analysis/ingest/text",
                          data={"text": text}, headers=h)
    for i in range(20):
        # Share some entities between cases
        text = f"Phone {1000000000+i} email user{i}@test.com"
        await client.post(f"/api/v1/cases/{case2_id}/analysis/ingest/text",
                          data={"text": text}, headers=h)

    # Benchmark graph
    start = time.perf_counter()
    r = await client.get(f"/api/v1/cases/{case_id}/relationships/graph", headers=h)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert r.status_code == 200
    nodes = len(r.json().get("nodes", []))
    edges = len(r.json().get("edges", []))
    print(f"\n  Medium graph: {nodes} nodes, {edges} edges, {elapsed_ms:.0f}ms")
    assert elapsed_ms < 10000, f"Graph took {elapsed_ms:.0f}ms — too slow"


@pytest.mark.asyncio
async def test_key_entities_benchmark(client: AsyncClient, auth_token):
    """Benchmark key entity analysis."""
    h = auth_headers(auth_token)

    r = await client.post("/api/v1/cases", json={"title": "Bench KE", "description": "perf"}, headers=h)
    case_id = r.json()["id"]

    for i in range(25):
        text = f"Phone {1000000000+i} email user{i}@test.com"
        await client.post(f"/api/v1/cases/{case_id}/analysis/ingest/text",
                          data={"text": text}, headers=h)

    start = time.perf_counter()
    r = await client.get(f"/api/v1/cases/{case_id}/analysis/key-entities", headers=h)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert r.status_code == 200
    print(f"\n  Key entities: {len(r.json())} entities, {elapsed_ms:.0f}ms")
    assert elapsed_ms < 5000


@pytest.mark.asyncio
async def test_patterns_benchmark(client: AsyncClient, auth_token):
    """Benchmark pattern detection."""
    h = auth_headers(auth_token)

    r = await client.post("/api/v1/cases", json={"title": "Bench Pat", "description": "perf"}, headers=h)
    case_id = r.json()["id"]

    for i in range(20):
        text = f"Phone {1000000000+i} email user{i}@test.com"
        await client.post(f"/api/v1/cases/{case_id}/analysis/ingest/text",
                          data={"text": text}, headers=h)

    start = time.perf_counter()
    r = await client.get(f"/api/v1/cases/{case_id}/analysis/patterns", headers=h)
    elapsed_ms = (time.perf_counter() - start) * 1000
    assert r.status_code == 200
    print(f"\n  Patterns: {len(r.json())} patterns, {elapsed_ms:.0f}ms")
    assert elapsed_ms < 5000
