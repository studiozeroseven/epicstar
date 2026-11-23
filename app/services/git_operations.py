"""Git operations via the git CLI.

Clone/push run as subprocesses (no shell) so the configured timeouts are
actually enforced and untrusted repo URLs never reach a shared process.
GitPython was dropped: it offers no timeout support and its URL handling
carried an RCE CVE class (CVE-2024-22192) on adversarial URLs.
"""

import os
import shutil
import subprocess  # nosec B404 - intentional: git CLI with fixed argv, no shell
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlsplit, urlunsplit

from app.config import settings
from app.core.logging import get_logger
from app.utils.exceptions import GitOperationError

logger = get_logger(__name__)


def redact_url(url: str) -> str:
    """Strip userinfo (credentials) from a URL before logging it."""
    try:
        parts = urlsplit(url)
        if parts.username or parts.password:
            netloc = parts.hostname or ""
            if parts.port:
                netloc = f"{netloc}:{parts.port}"
            return urlunsplit((parts.scheme, netloc, parts.path, parts.query, parts.fragment))
    except ValueError:
        pass
    return url


class GitOperations:
    """Git clone/push operations with enforced timeouts."""

    def __init__(self) -> None:
        """Initialize git operations."""
        self.temp_dir = settings.git_temp_dir
        self.clone_timeout = settings.git_clone_timeout
        self.push_timeout = settings.git_push_timeout
        self.clone_depth = settings.git_clone_depth
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)

    def _git(self, args: list[str], *, timeout: int) -> str:
        """Run git with fixed args (no shell) and a hard timeout.

        Credential prompts are disabled so a bad URL fails fast instead of
        hanging on stdin. URLs are redacted in logs and errors.
        """
        cmd = ["git", *args]
        redacted = " ".join(redact_url(a) if "://" in a else a for a in args)
        env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
        try:
            proc = subprocess.run(  # nosec B603 - fixed argv list, no shell, redacted
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=env,
            )
        except subprocess.TimeoutExpired:
            raise GitOperationError(f"git {redacted.split(' ', 2)[0]} timed out after {timeout}s")
        except OSError as e:
            raise GitOperationError(f"git executable error: {e}")

        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()[-500:]
            logger.error("git %s failed rc=%s: %s", redacted, proc.returncode, detail)
            raise GitOperationError(f"git {redacted} failed: {detail}")
        return proc.stdout

    def clone_repository(self, clone_url: str, branch: Optional[str] = None) -> str:
        """Clone a repository (bare) into a temp dir; returns the path."""
        temp_repo_dir = tempfile.mkdtemp(dir=self.temp_dir)
        args = [
            "-c",
            "credential.helper=",
            "clone",
            "--bare",
        ]
        if self.clone_depth > 0:
            args += ["--depth", str(self.clone_depth)]
        if branch:
            args += ["--branch", branch, "--single-branch"]
        args += [clone_url, temp_repo_dir]

        logger.info("Cloning %s", redact_url(clone_url))
        try:
            self._git(args, timeout=self.clone_timeout)
            logger.info("Cloned to %s", temp_repo_dir)
            return temp_repo_dir
        except GitOperationError:
            self.cleanup_directory(temp_repo_dir)
            raise
        except Exception as e:
            self.cleanup_directory(temp_repo_dir)
            raise GitOperationError(f"Unexpected clone error: {e}") from e

    def push_repository(
        self, repo_path: str, remote_url: str, branch: Optional[str] = None
    ) -> None:
        """Push refs from a bare repo to the target remote."""
        base_args = ["-C", repo_path, "-c", "credential.helper=", "push"]

        logger.info("Pushing to %s", redact_url(remote_url))
        try:
            if branch:
                self._git([*base_args, remote_url, branch], timeout=self.push_timeout)
            else:
                # Push all branches, then tags (a bare clone holds both).
                self._git([*base_args, remote_url, "--all"], timeout=self.push_timeout)
                self._git([*base_args, remote_url, "--tags"], timeout=self.push_timeout)
            logger.info("Pushed %s", redact_url(remote_url))
        except GitOperationError:
            raise
        except Exception as e:
            raise GitOperationError(f"Unexpected push error: {e}") from e

    def sync_repository(
        self,
        source_url: str,
        target_url: str,
        branch: Optional[str] = None,
    ) -> None:
        """Sync a repository from source to target (clone then push)."""
        repo_path: Optional[str] = None
        try:
            repo_path = self.clone_repository(source_url, branch)
            self.push_repository(repo_path, target_url, branch)
        finally:
            if repo_path:
                self.cleanup_directory(repo_path)

    def cleanup_directory(self, path: str) -> None:
        """Remove a temporary working directory, ignoring errors."""
        try:
            if os.path.exists(path):
                shutil.rmtree(path, ignore_errors=True)
                logger.debug("Cleaned up directory: %s", path)
        except Exception as e:
            logger.warning("Failed to cleanup directory %s: %s", path, e)
