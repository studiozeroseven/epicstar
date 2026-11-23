"""Unit tests for git operations (local bare repos; no network needed)."""

import subprocess
import time
from pathlib import Path

import pytest

from app.config import settings
from app.services.git_operations import GitOperations, redact_url
from app.utils.exceptions import GitOperationError


def _run_git(*args, cwd=None):
    subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        env={
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t",
            "HOME": str(Path.home()),
        },
    )


@pytest.fixture(scope="module")
def workdir(tmp_path_factory):
    """A working repo with 2 commits, and an empty bare target repo."""
    base = tmp_path_factory.mktemp("git")
    source = base / "source"
    target = base / "target.git"

    _run_git("init", "-b", "main", str(source))
    (source / "README.md").write_text("hello")
    _run_git("-C", str(source), "add", "-A")
    _run_git("-C", str(source), "commit", "-m", "c1")
    (source / "docs.txt").write_text("v2")
    _run_git("-C", str(source), "add", "-A")
    _run_git("-C", str(source), "commit", "-m", "c2")
    _run_git("-C", str(source), "tag", "v1.0")

    _run_git("init", "--bare", "-b", "main", str(target))
    _run_git("-C", str(source), "remote", "add", "target", str(target))
    _run_git("-C", str(source), "push", "target", "main")

    return {"base": base, "source": source, "target": target}


class TestSyncRepository:
    def test_clone_and_push_roundtrip(self, workdir, monkeypatch):
        ops = GitOperations()
        source_url = f"file://{workdir['source']}"
        target_url = f"file://{workdir['target']}"

        # Fresh empty target to prove the roundtrip.
        fresh_target = workdir["base"] / "fresh.git"
        _run_git("init", "--bare", "-b", "main", str(fresh_target))

        ops.sync_repository(source_url, str(fresh_target))

        # The branch tip must now exist on the target.
        out = subprocess.run(
            ["git", "-C", str(fresh_target), "rev-parse", "refs/heads/main"],
            capture_output=True,
            text=True,
            check=True,
        )
        ours = subprocess.run(
            ["git", "-C", str(workdir["source"]), "rev-parse", "refs/heads/main"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert out.stdout.strip() == ours.stdout.strip()
        # Tags were pushed too.
        r = subprocess.run(["git", "-C", str(fresh_target), "tag"], capture_output=True, text=True)
        assert "v1.0" in r.stdout.split()

    def test_branch_scoped_sync(self, workdir):
        ops = GitOperations()
        target = workdir["base"] / "branch-only.git"
        _run_git("init", "--bare", "-b", "main", str(target))
        ops.sync_repository(f"file://{workdir['source']}", str(target), "main")
        out = subprocess.run(
            ["git", "-C", str(target), "rev-parse", "refs/heads/main"],
            capture_output=True,
            text=True,
            check=True,
        )
        assert len(out.stdout.strip()) == 40

    def test_bad_url_fails_fast(self):
        ops = GitOperations()
        with pytest.raises(GitOperationError):
            ops.sync_repository("https://.invalid-host.example/x.git", "file:///tmp/nope.git")

    def test_timeouts_are_enforced(self, workdir):
        ops = GitOperations()
        # A clone that cannot finish inside a 1ms timeout raises.
        with pytest.raises(GitOperationError, match="timed out"):
            ops._git(["clone", "file:///dev/random-slow-repo", "/tmp/nope"], timeout=0)

    def test_credentials_never_in_logs_or_errors(self, workdir, monkeypatch):
        ops = GitOperations()
        secret_url = "https://user:supersecret@example.invalid/repo.git"
        with pytest.raises(GitOperationError) as excinfo:
            ops.sync_repository(secret_url, "file:///tmp/nowhere-target.git")
        assert "supersecret" not in str(excinfo.value)
        assert "user:" not in str(excinfo.value)


class TestRedactUrl:
    def test_redact_url_strips_userinfo(self):
        assert redact_url("https://u:secret@host.tld/p.git") == "https://host.tld/p.git"

    def test_redact_url_keeps_query_and_fragment(self):
        assert redact_url("https://u@host.tld/p.git?x=1#frag") == "https://host.tld/p.git?x=1#frag"

    def test_redact_url_passthrough(self):
        assert redact_url("not a url") == "not a url"


class TestTempDir:
    def test_temp_directory_created(self, monkeypatch):
        test_dir = f"/tmp/epicstar-gitops-{time.monotonic_ns()}"
        monkeypatch.setattr(settings, "git_temp_dir", test_dir)
        GitOperations()
        assert Path(test_dir).exists()
