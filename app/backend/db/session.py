"""Database session management."""

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from config import settings
from db.models import Base


# Sync engine for migrations and CLI operations
sync_engine = create_engine(
    settings.database_url,
    poolclass=StaticPool,
    echo=settings.env == "dev"
)

# Async engine for FastAPI
async_engine = create_async_engine(
    settings.async_database_url,
    echo=settings.env == "dev",
    pool_pre_ping=True,
    pool_recycle=300
)

# Session factories
SyncSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=sync_engine
)

AsyncSessionLocal = sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


def get_sync_db() -> Session:
    """Get a synchronous database session."""
    db = SyncSessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_async_db() -> AsyncSession:
    """Get an asynchronous database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def create_tables():
    """Create all database tables."""
    Base.metadata.create_all(bind=sync_engine)


def drop_tables():
    """Drop all database tables."""
    Base.metadata.drop_all(bind=sync_engine)
