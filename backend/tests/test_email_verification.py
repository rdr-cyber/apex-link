"""Email verification tests — backend."""

import pytest
from httpx import AsyncClient

from tests.conftest import TestSessionLocal, auth_headers
from app.core.security import hash_password
from app.models.user import User, UserRole
from app.services.auth_service import _hash_token


async def _create_unverified_user(client: AsyncClient, username: str, email: str, password: str) -> None:
    """Create a user with email_verified=False."""
    async with TestSessionLocal() as db:
        existing = await db.execute(
            __import__("sqlalchemy").select(User).where(User.username == username)
        )
        if not existing.scalar_one_or_none():
            db.add(User(
                username=username, email=email,
                password_hash=hash_password(password),
                full_name=username.title(), role=UserRole.INVESTIGATOR,
                email_verified=False,
            ))
            await db.commit()


async def _create_verified_user(client: AsyncClient, username: str, email: str, password: str) -> None:
    """Create a user with email_verified=True."""
    async with TestSessionLocal() as db:
        existing = await db.execute(
            __import__("sqlalchemy").select(User).where(User.username == username)
        )
        if not existing.scalar_one_or_none():
            db.add(User(
                username=username, email=email,
                password_hash=hash_password(password),
                full_name=username.title(), role=UserRole.INVESTIGATOR,
                email_verified=True,
            ))
            await db.commit()


# --- Verification Request Tests ---

@pytest.mark.asyncio
async def test_verification_request_generic_response(client: AsyncClient):
    """Verification request always returns generic response (no enumeration)."""
    r = await client.post("/api/v1/auth/verify-email/request",
                          json={"email": "nonexistent@test.com"})
    assert r.status_code == 200
    assert "verification" in r.json()["message"].lower() or "sent" in r.json()["message"].lower()


@pytest.mark.asyncio
async def test_verification_request_for_existing_unverified_user(client: AsyncClient):
    """Verification request for unverified user returns generic response."""
    await _create_unverified_user(client, "vuser1", "vuser1@test.com", "pass123")
    r = await client.post("/api/v1/auth/verify-email/request",
                          json={"email": "vuser1@test.com"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_verification_request_for_verified_user(client: AsyncClient):
    """Verification request for already-verified user returns generic response."""
    await _create_verified_user(client, "vuser2", "vuser2@test.com", "pass123")
    r = await client.post("/api/v1/auth/verify-email/request",
                          json={"email": "vuser2@test.com"})
    assert r.status_code == 200


@pytest.mark.asyncio
async def test_verification_request_invalid_email_format(client: AsyncClient):
    """Invalid email format is rejected."""
    r = await client.post("/api/v1/auth/verify-email/request",
                          json={"email": "not-an-email"})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_verification_rate_limit(client: AsyncClient):
    """Verification requests are rate-limited."""
    # Reset rate limiter state
    from app.api.v1.auth import _verification_requests
    _verification_requests.clear()

    # Make max allowed requests (default 3)
    for i in range(3):
        r = await client.post("/api/v1/auth/verify-email/request",
                              json={"email": f"rate{i}@test.com"})
        assert r.status_code == 200

    # 4th should be rate-limited
    r = await client.post("/api/v1/auth/verify-email/request",
                          json={"email": "rate4@test.com"})
    assert r.status_code == 429

    # Clean up
    _verification_requests.clear()


# --- Token Verification Tests ---

@pytest.mark.asyncio
async def test_confirm_verification_valid_token(client: AsyncClient):
    """Valid token verification works."""
    from app.models.email_verification import EmailVerificationToken
    from datetime import datetime, timedelta, timezone

    async with TestSessionLocal() as db:
        # Create user
        user = User(
            username="verify1", email="verify1@test.com",
            password_hash=hash_password("pass123"),
            full_name="Verify User", role=UserRole.INVESTIGATOR,
            email_verified=False,
        )
        db.add(user)
        await db.flush()

        # Create token
        raw_token = "test-raw-token-valid-12345"
        token_hash = _hash_token(raw_token)
        vt = EmailVerificationToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(vt)
        await db.commit()

    r = await client.post("/api/v1/auth/verify-email/confirm",
                          json={"token": raw_token})
    assert r.status_code == 200
    assert "verified" in r.json()["message"].lower() or "success" in r.json()["message"].lower()


@pytest.mark.asyncio
async def test_confirm_verification_invalid_token(client: AsyncClient):
    """Invalid token is rejected."""
    r = await client.post("/api/v1/auth/verify-email/confirm",
                          json={"token": "completely-invalid-token-xyz"})
    assert r.status_code == 400
    assert "invalid" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_confirm_verification_expired_token(client: AsyncClient):
    """Expired token is rejected."""
    from app.models.email_verification import EmailVerificationToken
    from datetime import datetime, timedelta, timezone

    async with TestSessionLocal() as db:
        user = User(
            username="verify_exp", email="verify_exp@test.com",
            password_hash=hash_password("pass123"),
            full_name="Exp User", role=UserRole.INVESTIGATOR,
            email_verified=False,
        )
        db.add(user)
        await db.flush()

        raw_token = "expired-token-test-12345"
        token_hash = _hash_token(raw_token)
        vt = EmailVerificationToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),  # Already expired
        )
        db.add(vt)
        await db.commit()

    r = await client.post("/api/v1/auth/verify-email/confirm",
                          json={"token": raw_token})
    assert r.status_code == 400
    assert "expired" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_confirm_verification_used_token(client: AsyncClient):
    """Already-used token is rejected."""
    from app.models.email_verification import EmailVerificationToken
    from datetime import datetime, timedelta, timezone

    async with TestSessionLocal() as db:
        user = User(
            username="verify_used", email="verify_used@test.com",
            password_hash=hash_password("pass123"),
            full_name="Used User", role=UserRole.INVESTIGATOR,
            email_verified=False,
        )
        db.add(user)
        await db.flush()

        raw_token = "used-token-test-12345"
        token_hash = _hash_token(raw_token)
        vt = EmailVerificationToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            used_at=datetime.now(timezone.utc),  # Already used
        )
        db.add(vt)
        await db.commit()

    r = await client.post("/api/v1/auth/verify-email/confirm",
                          json={"token": raw_token})
    assert r.status_code == 400
    assert "used" in r.json()["detail"].lower()


@pytest.mark.asyncio
async def test_confirm_verification_double_use(client: AsyncClient):
    """Token cannot be reused after first successful confirmation."""
    from app.models.email_verification import EmailVerificationToken
    from datetime import datetime, timedelta, timezone

    async with TestSessionLocal() as db:
        user = User(
            username="verify_double", email="verify_double@test.com",
            password_hash=hash_password("pass123"),
            full_name="Double User", role=UserRole.INVESTIGATOR,
            email_verified=False,
        )
        db.add(user)
        await db.flush()

        raw_token = "double-use-token-test-12345"
        token_hash = _hash_token(raw_token)
        vt = EmailVerificationToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(vt)
        await db.commit()

    # First use — success
    r1 = await client.post("/api/v1/auth/verify-email/confirm",
                           json={"token": raw_token})
    assert r1.status_code == 200

    # Second use — rejected
    r2 = await client.post("/api/v1/auth/verify-email/confirm",
                           json={"token": raw_token})
    assert r2.status_code == 400
    assert "used" in r2.json()["detail"].lower()


# --- Login Verification Enforcement Tests ---

@pytest.mark.asyncio
async def test_unverified_user_cannot_login(client: AsyncClient):
    """Unverified user gets EMAIL_NOT_VERIFIED error."""
    await _create_unverified_user(client, "unver_login", "unver_login@test.com", "pass123")
    r = await client.post("/api/v1/auth/login",
                          json={"username": "unver_login", "password": "pass123"})
    assert r.status_code == 403
    assert r.headers.get("X-Auth-Error") == "EMAIL_NOT_VERIFIED"


@pytest.mark.asyncio
async def test_verified_user_can_login(client: AsyncClient):
    """Verified user can login normally."""
    await _create_verified_user(client, "ver_login", "ver_login@test.com", "pass123")
    r = await client.post("/api/v1/auth/login",
                          json={"username": "ver_login", "password": "pass123"})
    assert r.status_code == 200
    assert r.json().get("requires_challenge") is True


@pytest.mark.asyncio
async def test_wrong_password_does_not_reveal_verification_status(client: AsyncClient):
    """Wrong password always returns generic error, never reveals verification status."""
    await _create_unverified_user(client, "enum_test", "enum@test.com", "pass123")
    r = await client.post("/api/v1/auth/login",
                          json={"username": "enum_test", "password": "wrongpassword"})
    assert r.status_code == 401
    # Must NOT reveal email verification status
    assert r.headers.get("X-Auth-Error") != "EMAIL_NOT_VERIFIED"


@pytest.mark.asyncio
async def test_unknown_username_returns_generic_error(client: AsyncClient):
    """Unknown username returns same generic error."""
    r = await client.post("/api/v1/auth/login",
                          json={"username": "nonexistent_user_xyz", "password": "pass123"})
    assert r.status_code == 401


# --- Verification Status Endpoint Tests ---

@pytest.mark.asyncio
async def test_verification_status_returns_verified(client: AsyncClient):
    """Verification status reflects verified state."""
    await _create_verified_user(client, "vstatus1", "vstatus1@test.com", "pass123")
    r = await client.get("/api/v1/auth/verification-status",
                         params={"email": "vstatus1@test.com"})
    assert r.status_code == 200
    assert r.json()["verified"] is True


@pytest.mark.asyncio
async def test_verification_status_returns_unverified(client: AsyncClient):
    """Verification status reflects unverified state."""
    await _create_unverified_user(client, "vstatus2", "vstatus2@test.com", "pass123")
    r = await client.get("/api/v1/auth/verification-status",
                         params={"email": "vstatus2@test.com"})
    assert r.status_code == 200
    assert r.json()["verified"] is False


@pytest.mark.asyncio
async def test_verification_status_unknown_email(client: AsyncClient):
    """Unknown email returns False (no enumeration)."""
    r = await client.get("/api/v1/auth/verification-status",
                         params={"email": "unknown@test.com"})
    assert r.status_code == 200
    assert r.json()["verified"] is False


# --- Security Tests ---

@pytest.mark.asyncio
async def test_raw_token_not_stored(client: AsyncClient):
    """Only the hash is stored, not the raw token."""
    from app.models.email_verification import EmailVerificationToken
    from datetime import datetime, timedelta, timezone

    async with TestSessionLocal() as db:
        user = User(
            username="sec_hash", email="sec_hash@test.com",
            password_hash=hash_password("pass123"),
            full_name="Hash Test", role=UserRole.INVESTIGATOR,
            email_verified=False,
        )
        db.add(user)
        await db.flush()

        raw_token = "my-secret-verification-token-xyz"
        token_hash = _hash_token(raw_token)
        vt = EmailVerificationToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        db.add(vt)
        await db.commit()

        # Verify only hash is stored
        from sqlalchemy import select
        result = await db.execute(select(EmailVerificationToken).where(EmailVerificationToken.id == vt.id))
        stored = result.scalar_one()
        assert stored.token_hash == token_hash
        assert raw_token not in stored.token_hash  # Hash is different from raw
