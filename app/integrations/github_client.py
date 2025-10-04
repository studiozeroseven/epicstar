"""GitHub API client."""

from typing import Dict, Optional

from github import Auth, Github, GithubException

from app.config import settings
from app.core.logging import get_logger
from app.utils.exceptions import GitHubAPIError

logger = get_logger(__name__)


class GitHubClient:
    """GitHub API client wrapper."""

    def __init__(self) -> None:
        """Initialize GitHub client."""
        try:
            private_key = settings.get_github_private_key()
            auth = Auth.AppAuth(int(settings.github_app_id), private_key)
            self.client = Github(auth=auth)
            logger.info("GitHub client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GitHub client: {e}")
            raise GitHubAPIError(f"GitHub client initialization failed: {e}")

    def get_repository_info(self, full_name: str) -> Dict[str, any]:
        """
        Get repository information.

        Args:
            full_name: Repository full name (owner/repo)

        Returns:
            Repository information dictionary

        Raises:
            GitHubAPIError: If API call fails
        """
        try:
            repo = self.client.get_repo(full_name)

            return {
                "id": repo.id,
                "name": repo.name,
                "full_name": repo.full_name,
                "owner": repo.owner.login,
                "clone_url": repo.clone_url,
                "html_url": repo.html_url,
                "default_branch": repo.default_branch,
                "private": repo.private,
                "size": repo.size,
                "description": repo.description,
                "language": repo.language,
                "stars": repo.stargazers_count,
                "forks": repo.forks_count,
            }
        except GithubException as e:
            logger.error(f"GitHub API error for {full_name}: {e}")
            raise GitHubAPIError(f"Failed to get repository info: {e}")
        except Exception as e:
            logger.error(f"Unexpected error getting repository {full_name}: {e}")
            raise GitHubAPIError(f"Unexpected error: {e}")

    def verify_access(self, full_name: str) -> bool:
        """
        Verify access to a repository.

        Args:
            full_name: Repository full name (owner/repo)

        Returns:
            True if accessible, False otherwise
        """
        try:
            self.client.get_repo(full_name)
            return True
        except GithubException:
            return False
        except Exception as e:
            logger.error(f"Error verifying access to {full_name}: {e}")
            return False

    def close(self) -> None:
        """Close GitHub client connection."""
        if hasattr(self, "client"):
            self.client.close()

