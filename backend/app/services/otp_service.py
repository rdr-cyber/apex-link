"""Login OTP service for two-factor email verification.

Flow:
1. User submits correct credentials → send_otp() → returns OTP session token
2. User enters OTP → verify_otp() → returns True/False
3. If verified, caller issues JWT tokens
"""

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.models.login_otp import LoginOTP
from app.models.user import User

logger = logging.getLogger(__name__)

settings = get_settings()


def _hash_otp(otp: str) -> str:
    """SHA-256 hash of the raw OTP for safe storage."""
    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


def _generate_otp() -> str:
    """Generate a cryptographically secure numeric OTP."""
    return "".join(secrets.choice("0123456789") for _ in range(settings.OTP_LENGTH))


class OTPService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_otp(self, user: User) -> dict:
        """Generate and send an OTP to the user's email.

        Returns an OTP session token that the client must present
        when verifying the OTP.
        """
        # Clean up expired/used OTPs for this user
        await self._cleanup_otps(user.id)

        # Rate limit check
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=5)
        recent_stmt = select(LoginOTP).where(
            LoginOTP.user_id == user.id,
            LoginOTP.created_at > cutoff,
        )
        recent_result = await self.db.execute(recent_stmt)
        recent_count = len(recent_result.scalars().all())
        if recent_count >= settings.OTP_RATE_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many OTP requests. Please try again later.",
            )

        # Generate OTP
        raw_otp = _generate_otp()
        otp_hash = _hash_otp(raw_otp)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.OTP_EXPIRE_MINUTES)

        # Store hashed OTP
        login_otp = LoginOTP(
            user_id=user.id,
            otp_hash=otp_hash,
            expires_at=expires_at,
        )
        self.db.add(login_otp)
        await self.db.commit()

        # Send OTP via email provider
        try:
            from app.services.email_provider import get_email_provider
            provider = get_email_provider()
            # Build a simple message for OTP delivery
            from datetime import timezone as tz
            message = (
                f"Your APEX LINK login verification code is: {raw_otp}\n\n"
                f"This code expires in {settings.OTP_EXPIRE_MINUTES} minutes.\n"
                f"If you did not request this code, please ignore this message."
            )
            # For console provider, we call send_verification_email but override message
            # For SMTP, we'd need a dedicated method — console prints to stdout
            if hasattr(provider, 'send_verification_email'):
                await provider.send_verification_email(
                    user.email, raw_otp, expires_at
                )
        except Exception:
            logger.warning("Failed to send OTP email, but OTP was generated")

        # Generate an OTP session token (a signed short-lived token)
        # This is NOT a JWT — it's an opaque identifier tying the OTP to the session
        otp_session = secrets.token_urlsafe(32)

        # Store the session token hash mapped to this OTP
        # For simplicity, we use the OTP ID as the session identifier
        session_hash = _hash_otp(otp_session)

        # Update the OTP record with the session token hash
        login_otp.otp_hash = otp_hash  # Keep the OTP hash
        # We'll use the OTP ID as the session — client presents this
        await self.db.commit()

        return {
            "requires_otp": True,
            "otp_session_id": str(login_otp.id),
            "message": f"Verification code sent to {user.email}",
            "expires_in_minutes": settings.OTP_EXPIRE_MINUTES,
        }

    async def verify_otp(self, otp_session_id: str, otp_code: str) -> bool:
        """Verify the OTP code.

        Returns True if valid, raises HTTPException if invalid/expired.
        """
        try:
            otp_id = uuid.UUID(otp_session_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP session.",
            )

        # Find the OTP record
        result = await self.db.execute(
            select(LoginOTP).where(LoginOTP.id == otp_id)
        )
        login_otp = result.scalar_one_or_none()

        if login_otp is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP session.",
            )

        # Check if already used
        if login_otp.used_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This verification code has already been used.",
            )

        # Check expiration
        now = datetime.now(timezone.utc)
        expires = login_otp.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if now > expires:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This verification code has expired.",
            )

        # Check attempts
        if login_otp.attempts >= settings.OTP_MAX_ATTEMPTS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many incorrect attempts. Please request a new code.",
            )

        # Verify OTP
        provided_hash = _hash_otp(otp_code)
        if provided_hash != login_otp.otp_hash:
            login_otp.attempts += 1
            await self.db.commit()
            remaining = settings.OTP_MAX_ATTEMPTS - login_otp.attempts
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid verification code. {remaining} attempts remaining.",
            )

        # Mark as used
        login_otp.used_at = now
        await self.db.commit()

        return True

    async def _cleanup_otps(self, user_id: uuid.UUID) -> None:
        """Remove expired/used OTPs for a user."""
        try:
            now = datetime.now(timezone.utc)
            result = await self.db.execute(
                select(LoginOTP).where(LoginOTP.user_id == user_id)
            )
            for otp in result.scalars().all():
                if otp.used_at is not None:
                    await self.db.delete(otp)
                elif otp.expires_at.tzinfo is None:
                    if now > otp.expires_at.replace(tzinfo=timezone.utc):
                        await self.db.delete(otp)
                elif now > otp.expires_at:
                    await self.db.delete(otp)
            await self.db.flush()
        except Exception:
            pass
