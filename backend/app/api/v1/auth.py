"""Authentication routes with OTP two-factor verification."""

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.security import decode_token
from app.db.session import get_db
from app.models.user import User
from app.repositories.audit_repo import AuditLogRepository
from app.repositories.user_repo import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse, RefreshRequest, UserInfo
from app.services.auth_service import AuthService
from app.middleware.rate_limit import login_rate_limiter

router = APIRouter(prefix="/auth", tags=["Authentication"])


# --- Schemas ---

class VerificationRequest(BaseModel):
    email: EmailStr


class VerificationConfirm(BaseModel):
    token: str = Field(..., min_length=10, max_length=256)


class ChallengeVerifyRequest(BaseModel):
    challenge_id: str = Field(..., min_length=10, max_length=128)
    answer: str = Field(..., min_length=1, max_length=20)


# --- Rate Limiter for Verification Requests ---

from collections import defaultdict
import time

_verification_requests: dict[str, list[float]] = defaultdict(list)
VERIFICATION_RATE_WINDOW = 900  # 15 minutes


async def _check_verification_rate_limit(request: Request) -> None:
    """Rate limit verification requests: max 3 per 15 minutes per IP."""
    from app.core.settings import get_settings
    settings = get_settings()
    max_requests = settings.VERIFICATION_RATE_LIMIT

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        ip = forwarded.split(",")[0].strip()
    else:
        ip = request.client.host if request.client else "unknown"
    key = f"verify:{ip}"

    now = time.time()
    cutoff = now - VERIFICATION_RATE_WINDOW
    _verification_requests[key] = [t for t in _verification_requests[key] if t > cutoff]

    if len(_verification_requests[key]) >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many verification requests. Please try again later.",
        )
    _verification_requests[key].append(now)


# --- Routes ---

@router.post("/login", response_model=dict)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate a user. Returns challenge if credentials are valid."""
    await login_rate_limiter.check(request)

    ip = request.client.host if request.client else None

    # Validate credentials
    user_repo = UserRepository(db)
    from app.core.security import verify_password
    user = await user_repo.get_by_username(body.username)

    if user is None or not verify_password(body.password, user.password_hash):
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

    # Generate challenge
    from app.services.challenge_service import ChallengeService
    challenge_svc = ChallengeService(db)
    challenge = await challenge_svc.generate_challenge(user)

    # Audit
    audit_repo = AuditLogRepository(db)
    await audit_repo.log(
        user_id=user.id,
        action="CHALLENGE_ISSUED",
        resource_type="USER",
        resource_id=str(user.id),
        ip_address=ip,
    )

    return challenge


@router.post("/login/verify-challenge", response_model=TokenResponse)
async def verify_login_challenge(
    body: ChallengeVerifyRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Verify challenge answer and return JWT tokens."""
    from app.services.challenge_service import ChallengeService
    from app.core.security import create_access_token, create_refresh_token
    from app.core.settings import get_settings

    settings = get_settings()

    challenge_svc = ChallengeService(db)
    user = await challenge_svc.verify_challenge(body.challenge_id, body.answer)

    # Issue JWT tokens
    access_token = create_access_token(user.id, user.role.value)
    refresh_token = create_refresh_token(user.id)

    # Audit
    ip = request.client.host if request.client else None
    audit_repo = AuditLogRepository(db)
    await audit_repo.log(
        user_id=user.id,
        action="LOGIN",
        resource_type="USER",
        resource_id=str(user.id),
        ip_address=ip,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserInfo.model_validate(user),
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh an access token."""
    service = AuthService(db)
    return await service.refresh_token(body.refresh_token)


@router.get("/me", response_model=UserInfo)
async def get_me(
    user: User = Depends(get_current_user),
):
    """Get current user info."""
    return UserInfo.model_validate(user)


# --- Email Verification Endpoints ---

@router.post("/verify-email/request")
async def request_verification(
    body: VerificationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Request email verification. Always returns generic response."""
    await _check_verification_rate_limit(request)
    service = AuthService(db)
    result = await service.request_verification(body.email)

    # Audit
    from app.models.user import User as UserModel
    from sqlalchemy import select
    r = await db.execute(select(UserModel).where(UserModel.email == body.email.strip().lower()))
    u = r.scalar_one_or_none()
    if u:
        audit_repo = AuditLogRepository(db)
        await audit_repo.log(
            user_id=u.id,
            action="VERIFICATION_REQUESTED",
            resource_type="USER",
            resource_id=str(u.id),
        )

    return result


@router.post("/verify-email/confirm")
async def confirm_verification(
    body: VerificationConfirm,
    db: AsyncSession = Depends(get_db),
):
    """Confirm email verification with a token."""
    service = AuthService(db)
    result = await service.confirm_verification(body.token)

    # Audit
    from app.models.user import User as UserModel
    from app.models.email_verification import EmailVerificationToken
    from app.services.auth_service import _hash_token
    from sqlalchemy import select
    token_hash = _hash_token(body.token)
    r = await db.execute(select(EmailVerificationToken).where(EmailVerificationToken.token_hash == token_hash))
    vt = r.scalar_one_or_none()
    if vt:
        audit_repo = AuditLogRepository(db)
        await audit_repo.log(
            user_id=vt.user_id,
            action="EMAIL_VERIFIED",
            resource_type="USER",
            resource_id=str(vt.user_id),
        )

    return result


@router.get("/verification-status")
async def verification_status(
    email: str,
    db: AsyncSession = Depends(get_db),
):
    """Get email verification status. Safe from enumeration."""
    service = AuthService(db)
    return await service.get_verification_status(email)
