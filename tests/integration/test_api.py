"""Integration tests for API endpoints."""

import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test health check endpoint."""

    def test_health_check(self, client: TestClient):
        """Test health check returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "database" in data

    def test_root_endpoint(self, client: TestClient):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "version" in data


class TestWebhookEndpoint:
    """Test webhook endpoint."""

    def test_webhook_missing_signature(self, client: TestClient):
        """Test webhook with missing signature."""
        payload = {"action": "started", "repository": {"name": "test"}}

        response = client.post(
            "/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "watch",
                "X-GitHub-Delivery": "test-delivery-id",
            },
        )

        assert response.status_code == 401

    def test_webhook_invalid_signature(self, client: TestClient):
        """Test webhook with invalid signature."""
        payload = {"action": "started", "repository": {"name": "test"}}

        response = client.post(
            "/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "watch",
                "X-GitHub-Delivery": "test-delivery-id",
                "X-Hub-Signature-256": "sha256=invalid",
            },
        )

        assert response.status_code == 401

    def test_webhook_non_watch_event(self, client: TestClient):
        """Test webhook with non-watch event."""
        payload = {"action": "opened"}
        payload_bytes = json.dumps(payload).encode()

        # Calculate valid signature
        secret = "dev_webhook_secret_placeholder"
        signature = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()

        response = client.post(
            "/webhooks/github",
            content=payload_bytes,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-delivery-id",
                "X-Hub-Signature-256": f"sha256={signature}",
                "Content-Type": "application/json",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ignored"

