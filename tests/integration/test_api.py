"""Integration tests for API endpoints."""

from tests.conftest import post_webhook, sign, watch_payload


class TestHealthEndpoint:
    """Health and root endpoints."""

    def test_health_check(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert data["database"] == "connected"

    def test_root_endpoint(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "epicstar"
        assert "version" in data


class TestWebhookEndpoint:
    """Webhook endpoint validation and routing."""

    def test_webhook_missing_signature(self, client):
        response = client.post(
            "/webhooks/github",
            json={"action": "started"},
            headers={
                "X-GitHub-Event": "watch",
                "X-GitHub-Delivery": "d-1",
            },
        )
        assert response.status_code == 401

    def test_webhook_invalid_signature(self, client):
        response = client.post(
            "/webhooks/github",
            json={"action": "started"},
            headers={
                "X-GitHub-Event": "watch",
                "X-GitHub-Delivery": "d-1",
                "X-Hub-Signature-256": "sha256=invalid",
            },
        )
        assert response.status_code == 401

    def test_webhook_non_watch_event(self, client):
        body = b'{"action": "opened"}'
        response = client.post(
            "/webhooks/github",
            content=body,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "d-1",
                "X-Hub-Signature-256": sign(body),
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    def test_webhook_invalid_json(self, client):
        body = b"not json"
        response = client.post(
            "/webhooks/github",
            content=body,
            headers={
                "X-GitHub-Event": "watch",
                "X-GitHub-Delivery": "d-1",
                "X-Hub-Signature-256": sign(body),
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 400

    def test_webhook_invalid_watch_payload(self, client):
        # Valid signature, but missing required repository fields.
        body = b'{"action": "started"}'
        response = client.post(
            "/webhooks/github",
            content=body,
            headers={
                "X-GitHub-Event": "watch",
                "X-GitHub-Delivery": "d-1",
                "X-Hub-Signature-256": sign(body),
                "Content-Type": "application/json",
            },
        )
        assert response.status_code == 400

    def test_webhook_unstarted_action_ignored(self, client):
        payload = watch_payload()
        payload["action"] = "deleted"
        response = post_webhook(client, payload, delivery="d-ignore")
        assert response.status_code == 200
        assert response.json()["status"] == "ignored"
