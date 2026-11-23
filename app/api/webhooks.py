"""Webhook endpoints.

GitHub expects webhook handlers to answer quickly (<10s) or it treats the
delivery as timed out and redelivers. Syncs can run for minutes, so this
endpoint validates, records, and QUEUES the sync as a background task,
returning 202 immediately. Results land in the database (repositories /
sync_logs / webhook_events) and metrics.
"""

import asyncio
import json
from typing import Dict, Optional, Set

from fastapi import APIRouter, Header, Request, status
from fastapi.responses import JSONResponse

from app.api.metrics import (
    decrement_active_syncs,
    increment_active_syncs,
    record_sync_operation,
    record_webhook_request,
)
from app.core.logging import get_logger
from app.core.security import verify_github_signature
from app.models.webhook import WatchEvent
from app.services.sync_orchestrator import SyncOrchestrator

router = APIRouter()
logger = get_logger(__name__)

# Keep references to background tasks so they are not garbage-collected mid-run.
_background_tasks: Set[asyncio.Task] = set()


@router.post("/webhooks/github", status_code=status.HTTP_200_OK)
async def github_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_hub_signature_256: Optional[str] = Header(None, alias="X-Hub-Signature-256"),
) -> JSONResponse:
    """Receive (and queue) GitHub webhook events."""
    body = await request.body()

    # Verify signature
    if not verify_github_signature(body, x_hub_signature_256):
        logger.error(
            "Webhook signature verification failed",
            extra={"delivery_id": x_github_delivery, "event": x_github_event},
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"error": "Invalid signature"},
        )

    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError as e:
        logger.error(
            "Failed to parse webhook payload",
            extra={"delivery_id": x_github_delivery, "error": str(e)},
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Invalid JSON payload"},
        )

    logger.info(
        "Received webhook",
        extra={
            "event": x_github_event,
            "delivery_id": x_github_delivery,
            "action": payload.get("action") if isinstance(payload, dict) else None,
        },
    )

    # Only process watch events
    if x_github_event != "watch":
        logger.info(
            "Ignoring non-watch event",
            extra={"event": x_github_event, "delivery_id": x_github_delivery},
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ignored", "reason": "not a watch event"},
        )

    # Validate and parse watch event
    try:
        event = WatchEvent(**payload)
    except Exception as e:
        logger.error(
            "Failed to validate webhook payload",
            extra={"delivery_id": x_github_delivery, "error": str(e)},
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Invalid payload structure"},
        )

    # Only process "started" action (starred)
    if event.action != "started":
        logger.info(
            "Ignoring non-started action",
            extra={"action": event.action, "delivery_id": x_github_delivery},
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"status": "ignored", "reason": f"action is {event.action}, not started"},
        )

    record_webhook_request("watch", "received")

    # Queue the sync as a background task; respond immediately.
    task = asyncio.create_task(
        _run_sync_safely(event, x_github_delivery, event.repository.full_name)
    )
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)

    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "status": "queued",
            "delivery_id": x_github_delivery,
            "repository": event.repository.full_name,
        },
    )


async def _run_sync_safely(event: WatchEvent, delivery_id: str, full_name: str) -> None:
    """Run one sync, recording metrics; never raises."""
    increment_active_syncs()
    try:
        try:
            orchestrator = SyncOrchestrator()
            result = await orchestrator.process_star_event(event, delivery_id)
        except Exception:
            logger.exception(
                "Unexpected error syncing %s", full_name, extra={"delivery_id": delivery_id}
            )
            record_webhook_request("watch", "failed")
            record_sync_operation("failed", 0)
            return

        result_status = result.get("status", "failed")
        if result_status == "success":
            record_webhook_request("watch", "success")
            duration = result.get("duration_seconds", 0)
            record_sync_operation(
                "success", float(duration) if isinstance(duration, (int, float)) else 0
            )
        elif result_status == "already_synced":
            record_webhook_request("watch", "already_synced")
            record_sync_operation("already_synced", 0)
        else:
            record_webhook_request("watch", "failed")
            record_sync_operation("failed", 0)

        logger.info(
            "Webhook sync finished",
            extra={"delivery_id": delivery_id, "repository": full_name, "result": result},
        )
    finally:
        decrement_active_syncs()
