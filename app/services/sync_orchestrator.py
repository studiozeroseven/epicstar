"""Sync orchestration service."""

import time
from datetime import datetime
from typing import Dict

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.core.retry import with_retry
from app.db.crud import RepositoryCRUD, SyncLogCRUD, WebhookEventCRUD
from app.db.database import AsyncSessionLocal
from app.integrations.github_client import GitHubClient
from app.integrations.onedev_client import OneDevClient
from app.models.webhook import WatchEvent
from app.services.git_operations import GitOperations
from app.utils.exceptions import GitHubAPIError, GitOperationError, OneDevAPIError

logger = get_logger(__name__)


class SyncOrchestrator:
    """Orchestrates the synchronization process."""

    def __init__(self) -> None:
        """Initialize sync orchestrator."""
        self.github_client = GitHubClient()
        self.onedev_client = OneDevClient()
        self.git_ops = GitOperations()

    @with_retry(max_attempts=3, min_wait=4, max_wait=60)
    async def process_star_event(self, event: WatchEvent, delivery_id: str) -> Dict[str, any]:
        """
        Process a GitHub star event.

        Args:
            event: Watch event data
            delivery_id: Webhook delivery ID

        Returns:
            Processing result
        """
        start_time = time.time()
        repo_id = None

        async with AsyncSessionLocal() as session:
            try:
                # Store webhook event
                await WebhookEventCRUD.create(
                    session,
                    event_id=delivery_id,
                    event_type="watch",
                    payload=event.model_dump(),
                    signature="verified",
                    delivery_id=delivery_id,
                )
                await session.commit()

                # Check if repository already exists
                existing_repo = await RepositoryCRUD.get_by_github_url(
                    session, event.repository.clone_url
                )

                if existing_repo:
                    logger.info(
                        f"Repository {event.repository.full_name} already synced",
                        extra={"repo_id": existing_repo.id},
                    )
                    return {
                        "status": "already_synced",
                        "repository_id": existing_repo.id,
                        "onedev_url": existing_repo.onedev_url,
                    }

                # Create repository record
                repo = await RepositoryCRUD.create(
                    session,
                    github_url=event.repository.clone_url,
                    github_repo_name=event.repository.name,
                    github_owner=event.repository.owner.login,
                    github_full_name=event.repository.full_name,
                    github_repo_id=event.repository.id,
                    github_default_branch=event.repository.default_branch,
                    github_is_private=event.repository.private,
                    github_size_kb=event.repository.size,
                    sync_status="pending",
                )
                await session.commit()
                repo_id = repo.id

                logger.info(
                    f"Starting sync for {event.repository.full_name}",
                    extra={"repo_id": repo_id},
                )

                # Update status to in_progress
                await RepositoryCRUD.update_status(session, repo_id, "in_progress")
                await session.commit()

                # Generate OneDev repository name
                onedev_repo_name = self._generate_onedev_name(
                    event.repository.owner.login, event.repository.name
                )

                # Create OneDev repository
                onedev_repo = await self.onedev_client.create_repository(
                    name=onedev_repo_name,
                    description=f"Synced from GitHub: {event.repository.full_name}",
                )

                # Update repository with OneDev info
                await RepositoryCRUD.update_status(
                    session,
                    repo_id,
                    "cloning",
                    onedev_url=onedev_repo["url"],
                    onedev_repo_name=onedev_repo["name"],
                    onedev_project_id=onedev_repo["id"],
                )
                await session.commit()

                # Perform git sync
                self.git_ops.sync_repository(
                    source_url=event.repository.clone_url,
                    target_url=onedev_repo["git_url"],
                    branch=event.repository.default_branch,
                )

                # Update status to completed
                await RepositoryCRUD.update_status(
                    session,
                    repo_id,
                    "completed",
                    last_synced_at=datetime.utcnow(),
                )
                await session.commit()

                # Create success log
                duration = int(time.time() - start_time)
                await SyncLogCRUD.create(
                    session,
                    repository_id=repo_id,
                    event_type="star",
                    status="success",
                    duration_seconds=duration,
                )
                await session.commit()

                # Mark webhook as processed
                await WebhookEventCRUD.mark_processed(
                    session, delivery_id, repository_id=repo_id
                )
                await session.commit()

                logger.info(
                    f"Successfully synced {event.repository.full_name}",
                    extra={
                        "repo_id": repo_id,
                        "onedev_url": onedev_repo["url"],
                        "duration": duration,
                    },
                )

                return {
                    "status": "success",
                    "repository_id": repo_id,
                    "onedev_url": onedev_repo["url"],
                    "duration_seconds": duration,
                }

            except (GitHubAPIError, OneDevAPIError, GitOperationError) as e:
                logger.error(
                    f"Sync failed for {event.repository.full_name}: {e}",
                    extra={"repo_id": repo_id, "error": str(e)},
                )

                if repo_id:
                    await RepositoryCRUD.update_status(
                        session, repo_id, "failed", error_message=str(e)
                    )
                    await SyncLogCRUD.create(
                        session,
                        repository_id=repo_id,
                        event_type="star",
                        status="failed",
                        error_message=str(e),
                        duration_seconds=int(time.time() - start_time),
                    )
                    await session.commit()

                await WebhookEventCRUD.mark_processed(
                    session, delivery_id, repository_id=repo_id, error=str(e)
                )
                await session.commit()

                raise

            except Exception as e:
                logger.exception(
                    f"Unexpected error syncing {event.repository.full_name}",
                    extra={"repo_id": repo_id},
                )

                if repo_id:
                    await RepositoryCRUD.update_status(
                        session, repo_id, "failed", error_message=str(e)
                    )
                    await session.commit()

                raise

    def _generate_onedev_name(self, owner: str, repo: str) -> str:
        """
        Generate OneDev repository name.

        Args:
            owner: GitHub owner
            repo: GitHub repository name

        Returns:
            OneDev repository name
        """
        prefix = settings.onedev_repo_prefix
        # Sanitize name (OneDev may have naming restrictions)
        safe_name = f"{owner}-{repo}".replace(".", "-").replace("_", "-").lower()
        return f"{prefix}{safe_name}"

