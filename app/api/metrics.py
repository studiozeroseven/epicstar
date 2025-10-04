"""Prometheus metrics endpoints."""

from typing import Dict

from fastapi import APIRouter
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.responses import Response

from app.db.database import get_db_health

router = APIRouter()

# Metrics
webhook_requests_total = Counter(
    "webhook_requests_total",
    "Total number of webhook requests",
    ["event_type", "status"],
)

sync_operations_total = Counter(
    "sync_operations_total",
    "Total number of sync operations",
    ["status"],
)

sync_duration_seconds = Histogram(
    "sync_duration_seconds",
    "Duration of sync operations in seconds",
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
)

active_syncs = Gauge(
    "active_syncs",
    "Number of currently active sync operations",
)

repository_count = Gauge(
    "repository_count",
    "Total number of repositories synced",
)

database_health = Gauge(
    "database_health",
    "Database health status (1=connected, 0=disconnected)",
)


@router.get("/metrics")
async def metrics() -> Response:
    """
    Prometheus metrics endpoint.
    
    Returns metrics in Prometheus text format.
    """
    # Update database health metric
    db_status = await get_db_health()
    database_health.set(1 if db_status == "connected" else 0)
    
    # Generate metrics
    metrics_data = generate_latest()
    
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST,
    )


@router.get("/metrics/summary")
async def metrics_summary() -> Dict[str, any]:
    """
    Human-readable metrics summary.
    
    Returns a JSON summary of key metrics.
    """
    from app.db.crud import RepositoryCRUD
    from app.db.database import AsyncSessionLocal
    
    async with AsyncSessionLocal() as session:
        repo_crud = RepositoryCRUD(session)
        
        # Count repositories by status
        # Note: This is a simplified version. In production, add proper count methods to CRUD
        total_repos = 0  # Would query: SELECT COUNT(*) FROM repositories
        completed_repos = 0  # Would query: SELECT COUNT(*) FROM repositories WHERE status='completed'
        failed_repos = 0  # Would query: SELECT COUNT(*) FROM repositories WHERE status='failed'
        pending_repos = 0  # Would query: SELECT COUNT(*) FROM repositories WHERE status='pending'
    
    db_status = await get_db_health()
    
    return {
        "database": {
            "status": db_status,
            "healthy": db_status == "connected",
        },
        "repositories": {
            "total": total_repos,
            "completed": completed_repos,
            "failed": failed_repos,
            "pending": pending_repos,
        },
        "sync_operations": {
            "active": int(active_syncs._value.get()),
        },
    }


def record_webhook_request(event_type: str, status: str) -> None:
    """Record a webhook request."""
    webhook_requests_total.labels(event_type=event_type, status=status).inc()


def record_sync_operation(status: str, duration: float) -> None:
    """Record a sync operation."""
    sync_operations_total.labels(status=status).inc()
    sync_duration_seconds.observe(duration)


def increment_active_syncs() -> None:
    """Increment active syncs counter."""
    active_syncs.inc()


def decrement_active_syncs() -> None:
    """Decrement active syncs counter."""
    active_syncs.dec()


def set_repository_count(count: int) -> None:
    """Set repository count gauge."""
    repository_count.set(count)

