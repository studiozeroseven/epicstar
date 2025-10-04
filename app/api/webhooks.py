"""Webhook endpoints."""

import json
from typing import Dict

from fastapi import APIRouter, Header, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger
from app.core.security import verify_github_signature
from app.models.webhook import WatchEvent
from app.services.sync_orchestrator import SyncOrchestrator
from app.utils.exceptions import WebhookValidationError

router = APIRouter()
logger = get_logger(__name__)


@router.post("/webhooks/github", status_code=status.HTTP_200_OK)
async def github_webhook(
    request: Request,
    x_github_event: str = Header(..., alias="X-GitHub-Event"),
    x_github_delivery: str = Header(..., alias="X-GitHub-Delivery"),
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
) -> Dict[str, str]:
    """
    GitHub webhook endpoint.

    Args:
        request: FastAPI request object
        x_github_event: GitHub event type
        x_github_delivery: Delivery ID
        x_hub_signature_256: Webhook signature

    Returns:
        Success response
    """
    # Get raw body for signature verification
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
            "action": payload.get("action"),
        },
    )

    # Only process watch events
    if x_github_event != "watch":
        logger.info(
            "Ignoring non-watch event",
            extra={"event": x_github_event, "delivery_id": x_github_delivery},
        )
        return {"status": "ignored", "reason": "not a watch event"}

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
        return {"status": "ignored", "reason": f"action is {event.action}, not started"}

    # Process the sync
    try:
        orchestrator = SyncOrchestrator()
        result = await orchestrator.process_star_event(event, x_github_delivery)

        logger.info(
            "Webhook processed successfully",
            extra={
                "delivery_id": x_github_delivery,
                "repository": event.repository.full_name,
                "result": result,
            },
        )

        return {"status": "success", "result": result}

    except Exception as e:
        logger.exception(
            "Failed to process webhook",
            extra={
                "delivery_id": x_github_delivery,
                "repository": event.repository.full_name,
                "error": str(e),
            },
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"error": "Internal server error"},
        )

