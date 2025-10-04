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
    # SQLite (sync only)
    engine = create_engine(
        settings.database_url,
        connect_args={"check_same_thread": False} if is_sqlite else {},
        echo=False,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    if is_async:
        async with AsyncSessionLocal() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    else:
        # For SQLite, we'll use sync session wrapped in async
        session = SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


async def get_db_health() -> str:
    """Check database health."""
    try:
        if is_async:
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
        else:
            with SessionLocal() as session:
                session.execute(text("SELECT 1"))
        return "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return "disconnected"


async def init_db() -> None:
    """Initialize database tables."""
    if is_async:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    else:
        Base.metadata.create_all(bind=engine)
    logger.info("Database initialized")

