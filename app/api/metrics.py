"""Prometheus metrics endpoints."""

from typing import Any, Dict

from fastapi import APIRouter
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from sqlalchemy import func, select
from sqlalchemy.engine import Result
from starlette.responses import Response

from app.db.database import AsyncSessionLocal, get_db_health
from app.db.models import Repository

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


async def _repository_status_counts() -> Dict[str, int]:
    """Count repositories grouped by sync status."""
    async with AsyncSessionLocal() as session:
        result: Result = await session.execute(
            select(Repository.sync_status, func.count()).group_by(Repository.sync_status)
        )
    return dict(result.all())


@router.get("/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint (Prometheus text format)."""
    db_status = await get_db_health()
    database_health.set(1 if db_status == "connected" else 0)

    counts = await _repository_status_counts()
    repository_count.set(sum(counts.values()))

    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@router.get("/metrics/summary")
async def metrics_summary() -> Dict[str, Any]:
    """Human-readable JSON summary of key metrics."""
    db_status = await get_db_health()
    counts = await _repository_status_counts()

    return {
        "database": {
            "status": db_status,
            "healthy": db_status == "connected",
        },
        "repositories": {
            "total": sum(counts.values()),
            "completed": counts.get("completed", 0),
            "failed": counts.get("failed", 0),
            "pending": counts.get("pending", 0),
            "in_progress": counts.get("in_progress", 0),
            "cloning": counts.get("cloning", 0),
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
    """Increment active syncs gauge."""
    active_syncs.inc()


def decrement_active_syncs() -> None:
    """Decrement active syncs gauge, flooring at 0."""
    if active_syncs._value.get() > 0:
        active_syncs.dec()


def set_repository_count(count: int) -> None:
    """Set repository count gauge."""
    repository_count.set(count)
