"""
QorSense Database Configuration

Async SQLAlchemy setup with connection pooling and session management.
"""

import logging

from backend.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

logger = logging.getLogger(__name__)

# Create async engine with settings
# Create engine kwargs
engine_kwargs = {
    "echo": settings.database_echo,
    "pool_pre_ping": True,
    "pool_recycle": 3600,
}

# Apply pooling only for non-SQLite databases (Postgres)
if "sqlite" not in str(settings.database_url):
    engine_kwargs["pool_size"] = settings.database_pool_size
    engine_kwargs["max_overflow"] = settings.database_max_overflow

# Create async engine
engine = create_async_engine(
    settings.database_url,
    **engine_kwargs
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for models
Base = declarative_base()


async def get_db() -> AsyncSession:
    """
    Dependency for getting async database sessions.
    
    Yields:
        AsyncSession: Database session
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
