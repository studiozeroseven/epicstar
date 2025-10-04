"""Security utilities for webhook signature verification."""

import hashlib
import hmac
from typing import Optional

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def verify_github_signature(payload: bytes, signature_header: Optional[str]) -> bool:
    """
    Verify GitHub webhook signature.

    Args:
        payload: Raw request body bytes
        signature_header: X-Hub-Signature-256 header value

    Returns:
        True if signature is valid, False otherwise
    """
    if not signature_header:
        logger.warning("Missing signature header")
        return False

    if not signature_header.startswith("sha256="):
        logger.warning("Invalid signature format")
        return False

    # Extract signature from header
    received_signature = signature_header.split("=", 1)[1]

    # Calculate expected signature
    secret = settings.github_webhook_secret.encode("utf-8")
    expected_signature = hmac.new(secret, payload, hashlib.sha256).hexdigest()

    # Constant-time comparison
    is_valid = hmac.compare_digest(expected_signature, received_signature)

    if not is_valid:
        logger.warning("Invalid webhook signature")

    return is_valid

