"""Async SQLAlchemy session factory."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.settings import get_settings

settings = get_settings()

# Pool settings only apply to PostgreSQL — SQLite (tests) uses NullPool automatically
db_url = settings.DATABASE_URL
is_postgres = db_url.startswith("postgresql")

# For Supabase/managed PostgreSQL, SSL is typically required.
# asyncpg uses 'ssl' connect_arg; add it if DATABASE_URL doesn't already include sslmode.
import ssl as _ssl
_connect_args = {}
if is_postgres and "sslmode" not in db_url and "ssl" not in db_url:
    _connect_args["ssl"] = "require"

engine = create_async_engine(
    db_url,
    echo=settings.DEBUG,
    future=True,
    connect_args=_connect_args if _connect_args else None,
    **(
        {
            "pool_size": settings.DB_POOL_SIZE,
            "max_overflow": settings.DB_MAX_OVERFLOW,
            "pool_timeout": settings.DB_POOL_TIMEOUT,
            "pool_recycle": settings.DB_POOL_RECYCLE,
            "pool_pre_ping": True,
        }
        if is_postgres
        else {}
    ),
)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency that yields an async database session."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
