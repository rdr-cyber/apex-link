"""Authentication tests."""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, _login_with_challenge


@pytest.mark.asyncio
async def test_login_returns_challenge(client: AsyncClient, test_user):
    """Login with valid credentials should return challenge, not tokens."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data.get("requires_challenge") is True
    assert "challenge_id" in data
    assert "question" in data
    assert "+" in data["question"] or "-" in data["question"] or "x" in data["question"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "wrongpassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "nonexistent", "password": "password"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_challenge_verification_completes_login(client: AsyncClient, test_user):
    """Full challenge flow: credentials → challenge → JWT tokens."""
    token = await _login_with_challenge(client, "testuser", "testpass123")
    assert token is not None
    assert len(token) > 50  # JWT tokens are long


@pytest.mark.asyncio
async def test_challenge_wrong_answer_rejected(client: AsyncClient, test_user):
    """Wrong challenge answer should be rejected."""
    # Step 1: Get challenge
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass123"},
    )
    challenge_id = r.json()["challenge_id"]

    # Step 2: Wrong answer
    r2 = await client.post(
        "/api/v1/auth/login/verify-challenge",
        json={"challenge_id": challenge_id, "answer": "999999"},
    )
    assert r2.status_code == 400


@pytest.mark.asyncio
async def test_challenge_invalid_session_rejected(client: AsyncClient):
    """Invalid challenge ID should be rejected."""
    r = await client.post(
        "/api/v1/auth/login/verify-challenge",
        json={"challenge_id": "invalid-challenge-id-way-too-short", "answer": "42"},
    )
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_get_me(client: AsyncClient, test_user, auth_token):
    response = await client.get(
        "/api/v1/auth/me",
        headers=auth_headers(auth_token),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient):
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user):
    """Refresh token flow should work after challenge login."""
    # Step 1: Get challenge
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpass123"},
    )
    challenge_id = r.json()["challenge_id"]

    # Inject known answer
    from app.services.challenge_service import _challenges
    import hashlib
    challenge = _challenges[challenge_id]
    known_answer = "42"
    challenge["answer_hash"] = hashlib.sha256(known_answer.encode("utf-8")).hexdigest()

    # Step 2: Verify challenge
    r2 = await client.post(
        "/api/v1/auth/login/verify-challenge",
        json={"challenge_id": challenge_id, "answer": known_answer},
    )
    refresh_token = r2.json()["refresh_token"]

    # Step 3: Use refresh token
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient):
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid_token"},
    )
    assert response.status_code == 401
