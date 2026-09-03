"""Test configuration and fixtures."""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.security import hash_password
from app.db.session import Base, get_db
from app.main import app
from app.middleware.rate_limit import login_rate_limiter
from app.models.user import User, UserRole

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    """Reset all rate limiters between tests to avoid cross-test interference."""
    login_rate_limiter._requests.clear()
    from app.api.v1.auth import _verification_requests
    _verification_requests.clear()
    from app.services.challenge_service import clear_challenges
    clear_challenges()
    yield
    login_rate_limiter._requests.clear()
    _verification_requests.clear()
    clear_challenges()


test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def _init_db():
    """Create all tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)


@pytest_asyncio.fixture(scope="function")
async def client():
    """Full test client with fresh DB per test."""
    await _init_db()

    async def _override_get_db():
        async with TestSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def test_user(client: AsyncClient):
    """Create a test user via API by seeding the DB."""
    async with TestSessionLocal() as session:
        user = User(
            username="testuser",
            email="test@example.com",
            password_hash=hash_password("testpass123"),
            full_name="Test User",
            role=UserRole.INVESTIGATOR,
            email_verified=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture(scope="function")
async def test_admin(client: AsyncClient):
    """Create a test admin."""
    async with TestSessionLocal() as session:
        admin = User(
            username="testadmin",
            email="admin@example.com",
            password_hash=hash_password("adminpass123"),
            full_name="Test Admin",
            role=UserRole.ADMIN,
            email_verified=True,
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        return admin


async def _login_with_challenge(client: AsyncClient, username: str, password: str) -> str:
    """Complete the challenge-response login flow and return access token.

    1. POST /auth/login → get challenge_id and question
    2. Read the answer from the in-memory challenge store
    3. POST /auth/login/verify-challenge → get access_token
    """
    # Step 1: Submit credentials
    r = await client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password},
    )
    assert r.status_code == 200, f"Login failed: {r.text}"
    data = r.json()
    assert data.get("requires_challenge") is True, f"Expected challenge, got: {data}"
    challenge_id = data["challenge_id"]

    # Step 2: Read the answer from the in-memory challenge store
    from app.services.challenge_service import _challenges, _hash_answer
    challenge = _challenges.get(challenge_id)
    assert challenge is not None, "Challenge not found in store"

    # We stored the hash, not the answer. Inject the answer directly.
    # Since we control the challenge store, we can just set a known answer.
    import hashlib
    known_answer = "42"
    challenge["answer_hash"] = hashlib.sha256(known_answer.encode("utf-8")).hexdigest()

    # Step 3: Verify challenge
    r2 = await client.post(
        "/api/v1/auth/login/verify-challenge",
        json={"challenge_id": challenge_id, "answer": known_answer},
    )
    assert r2.status_code == 200, f"Challenge verification failed: {r2.text}"
    return r2.json()["access_token"]


@pytest_asyncio.fixture(scope="function")
async def auth_token(client: AsyncClient, test_user: User) -> str:
    """Get a JWT token for the test investigator user via challenge flow."""
    return await _login_with_challenge(client, "testuser", "testpass123")


@pytest_asyncio.fixture(scope="function")
async def admin_token(client: AsyncClient, test_admin) -> str:
    """Get a JWT token for the test admin user via challenge flow."""
    return await _login_with_challenge(client, "testadmin", "adminpass123")


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
