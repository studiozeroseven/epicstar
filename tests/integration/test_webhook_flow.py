"""Integration tests for the full webhook sync flow (OneDev + git mocked)."""

import pytest
from fastapi.testclient import TestClient

from app.integrations.onedev_client import OneDevClient
from app.services.git_operations import GitOperations
from app.utils.exceptions import OneDevAPIError
from tests.conftest import poll_until, post_webhook, table_rows, watch_payload


class _FakeOnedev:
    """Records calls; returns plausible get_or_create results."""

    def __init__(self):
        self.created = []
        self.fail_next = False
        self.call_count = 0

    async def __call__(self, self_outer, name: str, description=None):
        self.call_count += 1
        if self.fail_next:
            raise OneDevAPIError("OneDev create failed (simulated)")
        self.created.append(name)
        return {
            "id": 4242,
            "name": name,
            "path": name,
            "web_url": f"https://test.onedev.example.com/{name}",
            "git_url": f"https://user:token@test.onedev.example.com/{name}.git",
        }


class _FakeGit:
    def __init__(self):
        self.synced = []

    def __call__(self, source, target, branch):
        self.synced.append((source, target, branch))


@pytest.fixture
def fake_onedev(monkeypatch):
    fake = _FakeOnedev()

    async def fake_get_or_create(self, name, description=None):
        return await fake(self, name, description)

    monkeypatch.setattr(OneDevClient, "get_or_create_repository", fake_get_or_create)
    return fake


@pytest.fixture
def fake_git(monkeypatch):
    fake = _FakeGit()

    def fake_sync(self, source, target, branch):
        fake(source, target, branch)

    monkeypatch.setattr(GitOperations, "sync_repository", fake_sync)
    return fake


def wait_terminal(
    repo_full_name: str,
    until: str = "completed",
    timeout: float = 5.0,
) -> dict:
    """Poll until the repo row reaches the given terminal status."""
    import time

    deadline = time.time() + timeout
    last = None
    while time.time() < deadline:
        rows = [r for r in table_rows("repositories") if r["github_full_name"] == repo_full_name]
        last = rows[0] if rows else None
        if last and last["sync_status"] == until:
            return last
        time.sleep(0.02)
    raise AssertionError(
        f"repo {repo_full_name} never reached {until!r}"
        f" (last: {last['sync_status'] if last else None})"
    )


class TestStarFlow:
    """End-to-end star -> sync flow with external services stubbed."""

    def test_star_success_creates_repo_and_logs(
        self, client: TestClient, fake_onedev, fake_git, db
    ):
        payload = watch_payload(repo="octocat/hello-world", name="hello-world")
        response = post_webhook(client, payload, delivery="deliv-1")

        assert response.status_code == 202
        assert response.json()["status"] == "queued"

        row = wait_terminal("octocat/hello-world")
        assert row["sync_status"] == "completed"
        assert row["onedev_project_id"] == 4242
        assert row["onedev_repo_name"].startswith("github-")

        # OneDev got one get-or-create call; git got clone+push with cred URL.
        assert len(fake_onedev.created) == 1
        assert len(fake_git.synced) == 1
        source, target, branch = fake_git.synced[0]
        assert source == "https://github.com/octocat/hello-world.git"
        assert target.startswith("https://")
        assert "token@" in target
        assert branch == "main"

        # Sync log recorded a success.
        logs = [l for l in db.sync_logs() if l["repository_id"] == row["id"]]
        assert any(l["status"] == "success" for l in logs)

        # Webhook event stored with serialized starred_at (the datetime trap).
        events = [e for e in db.webhook_events() if e["event_id"] == "deliv-1"]
        assert len(events) == 1
        assert events[0]["processed"] == 1
        assert json_load(events[0]["payload"])["starred_at"] == "2026-11-23T15:00:00Z"

        # Metrics summary reflects real data (was hardcoded zeros before).
        summary = client.get("/metrics/summary").json()
        assert summary["repositories"]["completed"] >= 1
        assert summary["repositories"]["total"] >= 1

    def test_second_star_returns_already_synced(
        self, client: TestClient, fake_onedev, fake_git, db
    ):
        payload = watch_payload(repo="octocat/twice", name="twice")
        post_webhook(client, payload, delivery="deliv-2a")
        wait_terminal("octocat/twice")

        response = post_webhook(client, payload, delivery="deliv-2b")
        assert response.status_code in (200, 202)

        assert poll_until(
            lambda: any(
                e["event_id"] == "deliv-2b" and e["processed"] == 1 for e in db.webhook_events()
            )
        )
        # Only ONE OneDev call for the same repo (no duplicate sync).
        assert len(fake_onedev.created) == 1

        summary = client.get("/metrics/summary").json()
        assert summary["sync_operations"]["active"] == 0

    def test_onedev_failure_marks_repo_failed(self, client: TestClient, fake_onedev, fake_git, db):
        fake_onedev.fail_next = True
        payload = watch_payload(repo="octocat/broken", name="broken")
        response = post_webhook(client, payload, delivery="deliv-3")

        assert response.status_code == 202  # fails asynchronously, silently
        row = wait_terminal("octocat/broken", until="failed")
        assert row["sync_status"] == "failed"
        assert "OneDev create failed" in (row["error_message"] or "")

        # mark_processed commits slightly after the status update; poll for it.
        assert poll_until(
            lambda: any(
                e["processed"] == 1 and e["processing_error"] is not None
                for e in db.webhook_events()
                if e["event_id"] == "deliv-3"
            )
        ), "delivery was never marked processed"

        logs = [l for l in db.sync_logs() if l["repository_id"] == row["id"]]
        assert any(l["status"] == "failed" for l in logs)

        summary = client.get("/metrics/summary").json()
        assert summary["repositories"]["failed"] >= 1

    def test_failed_repo_is_retried_on_next_star(self, client: TestClient, fake_onedev, fake_git):
        payload = watch_payload(repo="octocat/recover", name="recover")

        fake_onedev.fail_next = True
        post_webhook(client, payload, delivery="deliv-4a")
        row = wait_terminal("octocat/recover", until="failed")
        assert row["sync_status"] == "failed"

        fake_onedev.fail_next = False
        post_webhook(client, payload, delivery="deliv-4b")
        row2 = wait_terminal("octocat/recover")
        assert row2["sync_status"] == "completed"

    def test_gauge_never_goes_negative_after_failure(
        self, client: TestClient, fake_onedev, fake_git
    ):
        fake_onedev.fail_next = True
        payload = watch_payload(repo="octocat/gauge", name="gauge")
        post_webhook(client, payload, delivery="deliv-5")
        wait_terminal("octocat/gauge", until="failed")
        summary = client.get("/metrics/summary").json()
        assert summary["sync_operations"]["active"] == 0


def json_load(raw):
    import json

    return json.loads(raw)
