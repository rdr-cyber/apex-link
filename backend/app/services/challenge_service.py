"""Login challenge-response service.

Generates simple visual math challenges that the user must solve
to complete login. No email or external service needed.

Flow:
1. User submits correct credentials → generate_challenge() → returns challenge
2. User solves challenge → verify_challenge() → returns user
3. Caller issues JWT tokens
"""

import hashlib
import logging
import random
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.settings import get_settings
from app.models.user import User

logger = logging.getLogger(__name__)

settings = get_settings()

# In-memory challenge store (replaces DB table for simplicity)
# challenge_id → {user_id, answer_hash, expires_at, used, attempts}
_challenges: dict[str, dict] = {}


def _hash_answer(answer: str) -> str:
    """SHA-256 hash of the answer for safe comparison."""
    return hashlib.sha256(answer.strip().lower().encode("utf-8")).hexdigest()


def _generate_challenge() -> tuple[str, str, str]:
    """Generate a simple math challenge.

    Returns (question, answer_str, answer_normalized).
    """
    challenge_type = random.choice(["add", "subtract", "multiply"])

    if challenge_type == "add":
        a = random.randint(10, 99)
        b = random.randint(10, 99)
        answer = a + b
        question = f"What is {a} + {b}?"
    elif challenge_type == "subtract":
        a = random.randint(20, 99)
        b = random.randint(10, a)
        answer = a - b
        question = f"What is {a} - {b}?"
    else:  # multiply
        a = random.randint(2, 12)
        b = random.randint(2, 12)
        answer = a * b
        question = f"What is {a} x {b}?"

    answer_str = str(answer)
    return question, answer_str, answer_str.strip().lower()


class ChallengeService:
    """Generates and verifies login challenges."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_challenge(self, user: User) -> dict:
        """Generate a new challenge for the user.

        Returns a dict with challenge_id, question, and expires_in_seconds.
        """
        question, answer_str, answer_normalized = _generate_challenge()
        answer_hash = _hash_answer(answer_normalized)

        # Generate unique challenge ID
        challenge_id = secrets.token_urlsafe(32)
        expires_in = settings.CHALLENGE_EXPIRE_SECONDS

        # Store challenge in memory
        _challenges[challenge_id] = {
            "user_id": user.id,
            "answer_hash": answer_hash,
            "expires_at": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
            "used": False,
            "attempts": 0,
            "question": question,
        }

        # Cleanup expired challenges
        self._cleanup_expired()

        logger.info(f"Challenge issued for user {user.username}: {question}")

        return {
            "requires_challenge": True,
            "challenge_id": challenge_id,
            "question": question,
            "expires_in_seconds": expires_in,
        }

    async def verify_challenge(self, challenge_id: str, answer: str) -> User:
        """Verify the challenge answer and return the user.

        Raises HTTPException on failure.
        """
        # Validate challenge_id format
        if not challenge_id or len(challenge_id) < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid challenge session.",
            )

        # Find the challenge
        challenge = _challenges.get(challenge_id)
        if challenge is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired challenge. Please try logging in again.",
            )

        # Check if already used
        if challenge["used"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This challenge has already been used. Please try logging in again.",
            )

        # Check expiration
        now = datetime.now(timezone.utc)
        if now > challenge["expires_at"]:
            del _challenges[challenge_id]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This challenge has expired. Please try logging in again.",
            )

        # Check attempts
        max_attempts = settings.CHALLENGE_MAX_ATTEMPTS
        if challenge["attempts"] >= max_attempts:
            del _challenges[challenge_id]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Too many incorrect attempts. Please try logging in again.",
            )

        # Verify answer
        provided_hash = _hash_answer(answer)
        if provided_hash != challenge["answer_hash"]:
            challenge["attempts"] += 1
            remaining = max_attempts - challenge["attempts"]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Incorrect answer. {remaining} attempts remaining.",
            )

        # Mark as used
        challenge["used"] = True

        # Fetch the user from DB
        user_result = await self.db.execute(
            select(User).where(User.id == challenge["user_id"])
        )
        user = user_result.scalar_one_or_none()

        if user is None or not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or inactive.",
            )

        return user

    def _cleanup_expired(self) -> None:
        """Remove expired challenges from memory."""
        now = datetime.now(timezone.utc)
        expired = [
            cid for cid, ch in _challenges.items()
            if now > ch["expires_at"]
        ]
        for cid in expired:
            del _challenges[cid]


def clear_challenges() -> None:
    """Clear all challenges. For testing only."""
    _challenges.clear()
