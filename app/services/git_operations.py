"""Git operations service."""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from git import Repo
from git.exc import GitCommandError

from app.config import settings
from app.core.logging import get_logger
from app.utils.exceptions import GitOperationError

logger = get_logger(__name__)


class GitOperations:
    """Git operations handler."""

    def __init__(self) -> None:
        """Initialize Git operations."""
        self.temp_dir = settings.git_temp_dir
        self.clone_timeout = settings.git_clone_timeout
        self.push_timeout = settings.git_push_timeout
        self.clone_depth = settings.git_clone_depth

        # Ensure temp directory exists
        Path(self.temp_dir).mkdir(parents=True, exist_ok=True)

    def clone_repository(self, clone_url: str, branch: Optional[str] = None) -> str:
        """
        Clone a repository.

        Args:
            clone_url: Repository clone URL
            branch: Branch to clone (default: None for default branch)

        Returns:
            Path to cloned repository

        Raises:
            GitOperationError: If clone fails
        """
        # Create temporary directory for this clone
        temp_repo_dir = tempfile.mkdtemp(dir=self.temp_dir)

        try:
            logger.info(f"Cloning repository from {clone_url}")

            clone_kwargs = {
                "depth": self.clone_depth if self.clone_depth > 0 else None,
            }

            if branch:
                clone_kwargs["branch"] = branch

            repo = Repo.clone_from(
                clone_url,
                temp_repo_dir,
                **clone_kwargs,
            )

            logger.info(f"Successfully cloned to {temp_repo_dir}")
            return temp_repo_dir

        except GitCommandError as e:
            logger.error(f"Git clone failed: {e}")
            self.cleanup_directory(temp_repo_dir)
            raise GitOperationError(f"Clone failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during clone: {e}")
            self.cleanup_directory(temp_repo_dir)
            raise GitOperationError(f"Unexpected clone error: {e}")

    def push_repository(
        self, repo_path: str, remote_url: str, branch: Optional[str] = None
    ) -> None:
        """
        Push repository to remote.

        Args:
            repo_path: Path to local repository
            remote_url: Remote URL to push to
            branch: Branch to push (default: None for all branches)

        Raises:
            GitOperationError: If push fails
        """
        try:
            repo = Repo(repo_path)

            # Add remote if it doesn't exist
            if "onedev" not in [remote.name for remote in repo.remotes]:
                repo.create_remote("onedev", remote_url)
            else:
                repo.remote("onedev").set_url(remote_url)

            logger.info(f"Pushing to {remote_url}")

            # Push all branches and tags
            if branch:
                repo.remote("onedev").push(branch, force=False)
            else:
                repo.remote("onedev").push(all=True, force=False)
                repo.remote("onedev").push(tags=True, force=False)

            logger.info("Successfully pushed to remote")

        except GitCommandError as e:
            logger.error(f"Git push failed: {e}")
            raise GitOperationError(f"Push failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error during push: {e}")
            raise GitOperationError(f"Unexpected push error: {e}")

    def sync_repository(
        self,
        source_url: str,
        target_url: str,
        branch: Optional[str] = None,
    ) -> None:
        """
        Sync repository from source to target.

        Args:
            source_url: Source repository URL
            target_url: Target repository URL
            branch: Branch to sync (default: None for all branches)

        Raises:
            GitOperationError: If sync fails
        """
        repo_path = None
        try:
            # Clone from source
            repo_path = self.clone_repository(source_url, branch)

            # Push to target
            self.push_repository(repo_path, target_url, branch)

            logger.info(f"Successfully synced from {source_url} to {target_url}")

        finally:
            # Cleanup
            if repo_path:
                self.cleanup_directory(repo_path)

    def cleanup_directory(self, path: str) -> None:
        """
        Clean up temporary directory.

        Args:
            path: Directory path to clean up
        """
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
                logger.debug(f"Cleaned up directory: {path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup directory {path}: {e}")

    def get_repository_size(self, repo_path: str) -> int:
        """
        Get repository size in bytes.

        Args:
            repo_path: Path to repository

        Returns:
            Size in bytes
        """
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(repo_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                if os.path.exists(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size

