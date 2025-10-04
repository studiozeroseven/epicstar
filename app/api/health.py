"""Health check endpoints."""

from typing import Dict

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.config import settings
from app.db.database import get_db_health

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    environment: str
    database: str


@router.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check() -> Dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Health status information
    """
    db_status = await get_db_health()

    return {
        "status": "healthy" if db_status == "connected" else "unhealthy",
        "version": settings.app_version,
        "environment": settings.environment,
        "database": db_status,
    }


@router.get("/", status_code=status.HTTP_200_OK)
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }

