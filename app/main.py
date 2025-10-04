"""Main FastAPI application."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.webhooks import router as webhook_router
from app.api.metrics import router as metrics_router
from app.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.database import init_db

# Setup logging
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info(f"Starting epicstar v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    yield

    # Shutdown
    logger.info("Shutting down application")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Automatically sync starred GitHub repositories to your private OneDev instance",
    lifespan=lifespan,
)

# CORS middleware
if settings.cors_enabled:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include routers
app.include_router(health_router, tags=["health"])
app.include_router(webhook_router, tags=["webhooks"])
app.include_router(metrics_router, tags=["metrics"])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower(),
    )

