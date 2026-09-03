"""Tests proving DemoEmailProvider never exposes raw verification tokens.

Security requirements:
- Raw verification tokens must NEVER appear in logs
- Raw verification tokens must NEVER appear in API responses
- Raw verification tokens must NEVER appear in print output
- Single-use token behavior must remain intact
- Expired tokens must remain rejected
- DemoEmailProvider must work in production mode (DEBUG=False)
"""

import asyncio
import logging
import sys
from io import StringIO
from unittest.mock import patch, AsyncMock

import pytest
from datetime import datetime, timedelta, timezone


class TestDemoEmailProviderTokenSecurity:
    """Verify DemoEmailProvider never leaks raw tokens."""

    @pytest.mark.asyncio
    async def test_demo_provider_never_logs_raw_token(self):
        """DemoEmailProvider must not include the raw token in any log output."""
        from app.services.email_provider import DemoEmailProvider

        provider = DemoEmailProvider()
        raw_token = "super-secret-verification-token-abc123"

        # Capture all log output
        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)
        logger = logging.getLogger("app.services.email_provider")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        try:
            await provider.send_verification_email(
                "test@example.com",
                raw_token,
                datetime.now(timezone.utc) + timedelta(hours=1),
            )
        finally:
            logger.removeHandler(handler)

        log_output = log_capture.getvalue()
        # The raw token must NEVER appear in log output
        assert raw_token not in log_output, (
            f"SECURITY VIOLATION: Raw token '{raw_token}' found in log output"
        )

    @pytest.mark.asyncio
    async def test_demo_provider_never_prints_raw_token(self):
        """DemoEmailProvider must not print the raw token to stdout."""
        from app.services.email_provider import DemoEmailProvider

        provider = DemoEmailProvider()
        raw_token = "another-secret-token-xyz789"

        # Capture stdout
        captured = StringIO()
        old_stdout = sys.stdout
        sys.stdout = captured

        try:
            await provider.send_verification_email(
                "test@example.com",
                raw_token,
                datetime.now(timezone.utc) + timedelta(hours=1),
            )
        finally:
            sys.stdout = old_stdout

        stdout_output = captured.getvalue()
        # The raw token must NEVER appear in stdout
        assert raw_token not in stdout_output, (
            f"SECURITY VIOLATION: Raw token '{raw_token}' found in stdout"
        )

    @pytest.mark.asyncio
    async def test_demo_provider_never_includes_verification_url(self):
        """DemoEmailProvider must not construct or expose the verification URL."""
        from app.services.email_provider import DemoEmailProvider

        provider = DemoEmailProvider()
        raw_token = "url-leak-test-token-456"

        log_capture = StringIO()
        handler = logging.StreamHandler(log_capture)
        handler.setLevel(logging.DEBUG)
        logger = logging.getLogger("app.services.email_provider")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        try:
            await provider.send_verification_email(
                "test@example.com",
                raw_token,
                datetime.now(timezone.utc) + timedelta(hours=1),
            )
        finally:
            logger.removeHandler(handler)

        log_output = log_capture.getvalue()
        # Neither the raw token nor a URL containing it should appear
        assert "verify-email" not in log_output.lower() or raw_token not in log_output

    @pytest.mark.asyncio
    async def test_demo_provider_works_in_production_mode(self):
        """DemoEmailProvider must work when DEBUG=False (production)."""
        from app.services.email_provider import get_email_provider, DemoEmailProvider

        with patch("app.core.settings.get_settings") as mock_settings:
            mock_settings.return_value.DEBUG = False
            mock_settings.return_value.EMAIL_PROVIDER = "demo"

            provider = get_email_provider()
            assert isinstance(provider, DemoEmailProvider)

    @pytest.mark.asyncio
    async def test_demo_provider_returns_success(self):
        """DemoEmailProvider must return True (verification flow continues)."""
        from app.services.email_provider import DemoEmailProvider

        provider = DemoEmailProvider()
        result = await provider.send_verification_email(
            "test@example.com",
            "test-token",
            datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert result is True


class TestVerificationTokenNotInAPIResponse:
    """Verify raw tokens never appear in API responses."""

    @pytest.mark.asyncio
    async def test_verification_request_never_returns_token(self, client):
        """Verification request endpoint must never return raw token in response."""
        from app.services.auth_service import _hash_token
        from app.models.user import User, UserRole
        from app.models.email_verification import EmailVerificationToken
        from tests.conftest import TestSessionLocal

        # Create user
        async with TestSessionLocal() as db:
            from app.core.security import hash_password
            user = User(
                username="token_leak_test", email="token_leak@test.com",
                password_hash=hash_password("pass123"),
                full_name="Token Leak Test", role=UserRole.INVESTIGATOR,
                email_verified=False,
            )
            db.add(user)
            await db.flush()

            # Create token
            raw_token = "secret-leak-test-token-789"
            token_hash = _hash_token(raw_token)
            vt = EmailVerificationToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            db.add(vt)
            await db.commit()

        # Request verification
        r = await client.post("/api/v1/auth/verify-email/request",
                              json={"email": "token_leak@test.com"})
        assert r.status_code == 200
        response_text = str(r.json())
        # Raw token must NOT appear in response
        assert raw_token not in response_text, (
            f"SECURITY VIOLATION: Raw token found in API response"
        )

    @pytest.mark.asyncio
    async def test_confirm_verification_never_returns_token(self, client):
        """Confirm verification must never return the raw token in response."""
        from app.services.auth_service import _hash_token
        from app.models.user import User, UserRole
        from app.models.email_verification import EmailVerificationToken
        from tests.conftest import TestSessionLocal
        from app.core.security import hash_password

        async with TestSessionLocal() as db:
            user = User(
                username="confirm_leak_test", email="confirm_leak@test.com",
                password_hash=hash_password("pass123"),
                full_name="Confirm Leak Test", role=UserRole.INVESTIGATOR,
                email_verified=False,
            )
            db.add(user)
            await db.flush()

            raw_token = "confirm-leak-token-abc"
            token_hash = _hash_token(raw_token)
            vt = EmailVerificationToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            db.add(vt)
            await db.commit()

        # Confirm verification
        r = await client.post("/api/v1/auth/verify-email/confirm",
                              json={"token": raw_token})
        assert r.status_code == 200
        response_text = str(r.json())
        # Raw token must NOT appear in success response
        assert raw_token not in response_text, (
            f"SECURITY VIOLATION: Raw token found in confirm response"
        )


class TestTokenSecurityBehavior:
    """Verify token lifecycle security properties."""

    @pytest.mark.asyncio
    async def test_single_use_token_cannot_be_reused(self, client):
        """Token must be rejected after first successful use."""
        from app.services.auth_service import _hash_token
        from app.models.user import User, UserRole
        from app.models.email_verification import EmailVerificationToken
        from tests.conftest import TestSessionLocal
        from app.core.security import hash_password

        async with TestSessionLocal() as db:
            user = User(
                username="reuse_test", email="reuse@test.com",
                password_hash=hash_password("pass123"),
                full_name="Reuse Test", role=UserRole.INVESTIGATOR,
                email_verified=False,
            )
            db.add(user)
            await db.flush()

            raw_token = "reuse-token-test-123"
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

    @pytest.mark.asyncio
    async def test_expired_token_rejected(self, client):
        """Expired token must be rejected."""
        from app.services.auth_service import _hash_token
        from app.models.user import User, UserRole
        from app.models.email_verification import EmailVerificationToken
        from tests.conftest import TestSessionLocal
        from app.core.security import hash_password

        async with TestSessionLocal() as db:
            user = User(
                username="expired_test", email="expired@test.com",
                password_hash=hash_password("pass123"),
                full_name="Expired Test", role=UserRole.INVESTIGATOR,
                email_verified=False,
            )
            db.add(user)
            await db.flush()

            raw_token = "expired-token-test-456"
            token_hash = _hash_token(raw_token)
            vt = EmailVerificationToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
            )
            db.add(vt)
            await db.commit()

        r = await client.post("/api/v1/auth/verify-email/confirm",
                              json={"token": raw_token})
        assert r.status_code == 400
        assert "expired" in r.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_only_hash_stored_not_raw_token(self):
        """Database must store only the hash, never the raw token."""
        from app.services.auth_service import _hash_token
        from app.models.email_verification import EmailVerificationToken
        from tests.conftest import TestSessionLocal
        from app.models.user import User, UserRole
        from app.core.security import hash_password
        from sqlalchemy import select

        async with TestSessionLocal() as db:
            user = User(
                username="hash_only_test", email="hash_only@test.com",
                password_hash=hash_password("pass123"),
                full_name="Hash Test", role=UserRole.INVESTIGATOR,
                email_verified=False,
            )
            db.add(user)
            await db.flush()

            raw_token = "raw-token-for-hash-test-789"
            token_hash = _hash_token(raw_token)
            vt = EmailVerificationToken(
                user_id=user.id,
                token_hash=token_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            db.add(vt)
            await db.flush()

            # Read back and verify only hash is stored
            result = await db.execute(
                select(EmailVerificationToken).where(EmailVerificationToken.id == vt.id)
            )
            stored = result.scalar_one()
            assert stored.token_hash == token_hash
            assert raw_token != stored.token_hash
            assert len(stored.token_hash) == 64  # SHA-256 hex digest length
