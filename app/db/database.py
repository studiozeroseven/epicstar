"""Database connection and session management."""

from typing import AsyncGenerator

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

Base = declarative_base()

# Determine if using async or sync engine
is_sqlite = settings.database_url.startswith("sqlite")
is_async = not is_sqlite

# Initialize session makers
AsyncSessionLocal = None
SessionLocal = None

if is_async:
    # PostgreSQL with asyncpg
    async_engine = create_async_engine(
        settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_recycle=settings.database_pool_recycle,
        echo=False,
    )
    AsyncSessionLocal = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
else:
    # SQLite with aiosqlite for async support
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False} if is_sqlite else {},
        echo=False,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    # Create async session for SQLite too
    async_engine = create_async_engine(
        settings.database_url.replace("sqlite://", "sqlite+aiosqlite://"),
        connect_args={"check_same_thread": False},
        echo=False,
    )
    AsyncSessionLocal = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_db_health() -> str:
    """Check database health."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        return "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return "disconnected"


async def init_db() -> None:
    """Initialize database tables."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")
