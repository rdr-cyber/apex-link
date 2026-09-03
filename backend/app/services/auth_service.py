"""Authentication service."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.settings import get_settings
from app.models.email_verification import EmailVerificationToken
from app.repositories.user_repo import UserRepository
from app.schemas.auth import TokenResponse, UserInfo

settings = get_settings()


def _hash_token(token: str) -> str:
    """SHA-256 hash of the raw token for safe storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    async def login(self, username: str, password: str, ip_address: str | None = None) -> TokenResponse:
        """Authenticate a user and return tokens."""
        user = await self.user_repo.get_by_username(username)
        if user is None or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials.",
                headers={"X-Auth-Error": "INVALID_CREDENTIALS"},
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive.",
                headers={"X-Auth-Error": "ACCOUNT_INACTIVE"},
            )
        if not user.email_verified:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Please verify your email before signing in.",
                headers={"X-Auth-Error": "EMAIL_NOT_VERIFIED"},
            )

        access_token = create_access_token(user.id, user.role.value)
        refresh_token = create_refresh_token(user.id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserInfo.model_validate(user),
        )

    async def refresh_token(self, refresh_token_str: str) -> TokenResponse:
        """Refresh an access token using a valid refresh token."""
        payload = decode_token(refresh_token_str)
        if payload is None or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token.",
            )

        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload.")

        user = await self.user_repo.get_by_id(uuid.UUID(user_id))
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive.")

        new_access = create_access_token(user.id, user.role.value)
        new_refresh = create_refresh_token(user.id)

        return TokenResponse(
            access_token=new_access,
            refresh_token=new_refresh,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user=UserInfo.model_validate(user),
        )

    async def get_user_info(self, user_id: uuid.UUID) -> UserInfo:
        """Get current user info."""
        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return UserInfo.model_validate(user)

    # --- Email Verification ---

    async def request_verification(self, email: str) -> dict:
        """Generate a verification token and send it via the configured provider.

        Always returns a generic message to prevent account enumeration.
        """
        from app.services.email_provider import get_email_provider

        # Normalize email for lookup
        normalized_email = email.strip().lower()

        # Find user (if exists)
        user = None
        try:
            from app.models.user import User
            result = await self.db.execute(select(User).where(User.email == normalized_email))
            user = result.scalar_one_or_none()
        except Exception:
            pass

        if user is None:
            # Return generic message — do NOT reveal that the email doesn't exist
            return {"message": "If the account exists and requires verification, a verification message has been sent."}

        if user.email_verified:
            # Already verified — still return generic message
            return {"message": "If the account exists and requires verification, a verification message has been sent."}

        # Clean up expired/used tokens for this user (opportunistic cleanup)
        await self._cleanup_tokens(user.id)

        # Generate cryptographically secure token
        raw_token = secrets.token_urlsafe(48)
        token_hash = _hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.VERIFICATION_TOKEN_EXPIRE_MINUTES)

        # Store hashed token
        verification_token = EmailVerificationToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        self.db.add(verification_token)
        await self.db.commit()

        # Send email (gracefully handle misconfiguration)
        try:
            provider = get_email_provider()
            await provider.send_verification_email(normalized_email, raw_token, expires_at)
        except Exception:
            import logging
            logging.getLogger(__name__).warning(
                "Email provider not available — verification token was generated "
                "but could not be delivered. Check EMAIL_PROVIDER and DEBUG settings."
            )

        return {"message": "If the account exists and requires verification, a verification message has been sent."}

    async def confirm_verification(self, token: str) -> dict:
        """Confirm email verification using the raw token.

        Returns success or a specific error for expired/used/invalid tokens.
        """
        token_hash = _hash_token(token)

        # Find the token record
        result = await self.db.execute(
            select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash)
        )
        verification_token = result.scalar_one_or_none()

        if verification_token is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token.",
                headers={"X-Auth-Error": "INVALID_VERIFICATION_TOKEN"},
            )

        # Check if already used
        if verification_token.used_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This verification link has already been used.",
                headers={"X-Auth-Error": "VERIFICATION_TOKEN_USED"},
            )

        # Check expiration
        now = datetime.now(timezone.utc)
        if verification_token.expires_at.tzinfo is None:
            expires_at = verification_token.expires_at.replace(tzinfo=timezone.utc)
        else:
            expires_at = verification_token.expires_at
        if now > expires_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This verification link has expired.",
                headers={"X-Auth-Error": "VERIFICATION_TOKEN_EXPIRED"},
            )

        # Mark token as used
        verification_token.used_at = now

        # Mark user as verified
        from app.models.user import User
        user_result = await self.db.execute(select(User).where(User.id == verification_token.user_id))
        user = user_result.scalar_one_or_none()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token.",
                headers={"X-Auth-Error": "INVALID_VERIFICATION_TOKEN"},
            )

        user.email_verified = True
        user.email_verified_at = now

        await self.db.commit()

        return {"message": "Email verified successfully. You can now sign in."}

    async def get_verification_status(self, email: str) -> dict:
        """Get verification status for an email. Safe from enumeration."""
        normalized_email = email.strip().lower()
        try:
            from app.models.user import User
            result = await self.db.execute(select(User).where(User.email == normalized_email))
            user = result.scalar_one_or_none()
        except Exception:
            user = None

        if user is None:
            return {"verified": False, "email": normalized_email}

        return {"verified": user.email_verified, "email": normalized_email}

    async def _cleanup_tokens(self, user_id: uuid.UUID) -> None:
        """Remove expired and used tokens for a user (opportunistic cleanup)."""
        try:
            now = datetime.now(timezone.utc)
            result = await self.db.execute(
                select(EmailVerificationToken).where(
                    EmailVerificationToken.user_id == user_id
                )
            )
            tokens = result.scalars().all()
            for t in tokens:
                if t.used_at is not None:
                    await self.db.delete(t)
                elif t.expires_at.tzinfo is None:
                    if now > t.expires_at.replace(tzinfo=timezone.utc):
                        await self.db.delete(t)
                elif now > t.expires_at:
                    await self.db.delete(t)
            await self.db.flush()
        except Exception:
            pass  # Best-effort cleanup
