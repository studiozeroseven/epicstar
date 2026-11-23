"""Pytest configuration.

The environment app.config requires is defaulted HERE, before any app
import, so the suite runs on a clean checkout with no .env present.
"""

import os
import tempfile

_TEST_DB = os.path.join(tempfile.gettempdir(), "epicstar-pytest.db")
if os.path.exists(_TEST_DB):
    os.remove(_TEST_DB)

# FORCE test configuration: env vars beat dotenv sources in pydantic-settings,
# so assigning (not setdefault) makes the suite immune to ambient env vars and
# any developer-local .env file.
_TEST_ENV = {
    "ENVIRONMENT": "testing",
    "GITHUB_APP_ID": "123456",
    "GITHUB_WEBHOOK_SECRET": "test_webhook_secret",
    "GITHUB_PRIVATE_KEY": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----",
    "ONEDEV_API_URL": "https://test.onedev.example.com",
    "ONEDEV_USERNAME": "test-user",
    "ONEDEV_API_TOKEN": "test_token",
    "RETRY_MIN_WAIT": "0.01",
    "RETRY_MAX_WAIT": "0.05",
    "RETRY_BACKOFF_FACTOR": "1",
    "DATABASE_URL": f"sqlite:///{_TEST_DB}",
}
os.environ.update(_TEST_ENV)

import hashlib  # noqa: E402
import hmac  # noqa: E402
import json  # noqa: E402
import sqlite3  # noqa: E402
import time  # noqa: E402
from typing import Any, Dict, Iterator  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

WEBHOOK_PATH = "/webhooks/github"


def db_path() -> str:
    """Absolute path of the test sqlite database."""
    return _TEST_DB


def table_rows(table: str) -> list[dict]:
    """Read all rows of a table straight from the sqlite file."""
    with sqlite3.connect(db_path()) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(r) for r in conn.execute(f"SELECT * FROM {table}").fetchall()]


def poll_until(predicate, timeout: float = 10.0, interval: float = 0.05) -> bool:
    """Poll a (sync) predicate until true or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


def sign(payload_bytes: bytes, secret: str = "test_webhook_secret") -> str:
    """Compute a valid GitHub webhook signature header value."""
    digest = hmac.new(secret.encode(), payload_bytes, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def watch_payload(
    repo: str = "octocat/hello-world",
    name: str = "hello-world",
    starred_at: str = "2026-11-23T15:00:00Z",
) -> Dict[str, Any]:
    """A realistic GitHub `watch` webhook body (includes starred_at)."""
    return {
        "action": "started",
        "starred_at": starred_at,
        "repository": {
            "id": 12345,
            "node_id": "R_12345",
            "name": name,
            "full_name": repo,
            "owner": {"login": repo.split("/")[0], "type": "User"},
            "html_url": f"https://github.com/{repo}",
            "clone_url": f"https://github.com/{repo}.git",
            "git_url": f"git://github.com/{repo}.git",
            "default_branch": "main",
            "private": False,
            "size": 100,
            "created_at": "2020-01-01T00:00:00Z",
            "pushed_at": "2026-01-01T00:00:00Z",
        },
        "sender": {"login": "ian"},
    }


def post_webhook(
    client: TestClient,
    body: Dict[str, Any],
    event: str = "watch",
    delivery: str = "delivery-1",
):
    """POST a signed webhook payload."""
    raw = json.dumps(body).encode()
    return client.post(
        WEBHOOK_PATH,
        content=raw,
        headers={
            "X-GitHub-Event": event,
            "X-GitHub-Delivery": delivery,
            "X-Hub-Signature-256": sign(raw),
            "Content-Type": "application/json",
        },
    )


@pytest.fixture
def client() -> Iterator[TestClient]:
    """Test client with real app lifespan + real sqlite database."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def db():
    """Assertion helpers reading the sqlite file directly."""

    class _DB:
        repositories = staticmethod(lambda: table_rows("repositories"))
        sync_logs = staticmethod(lambda: table_rows("sync_logs"))
        webhook_events = staticmethod(lambda: table_rows("webhook_events"))

    return _DB()
