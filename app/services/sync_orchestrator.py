"""Sync orchestration service.

The orchestrator persists each star event, then runs two externally-failing
steps - OneDev project creation and the git clone/push - each with its own
retry policy from settings. It returns one of: success, already_synced,
failed. Nothing here retries the whole flow, so a failed first attempt can
never resurface as a bogus already_synced result.
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger
from app.core.retry import retry_with_backoff
from app.db.crud import RepositoryCRUD, SyncLogCRUD, WebhookEventCRUD
from app.db.database import AsyncSessionLocal
from app.db.models import Repository
from app.integrations.onedev_client import OneDevClient
from app.models.webhook import WatchEvent
from app.services.git_operations import GitOperations
from app.utils.exceptions import GitOperationError, OneDevAPIError

logger = get_logger(__name__)


class SyncOrchestrator:
    """Orchestrates the synchronization process."""

    def __init__(self) -> None:
        """Initialize sync orchestrator."""
        self.onedev_client = OneDevClient()
        self.git_ops = GitOperations()

    async def process_star_event(self, event: WatchEvent, delivery_id: str) -> Dict[str, object]:
        """Process a GitHub star event; never raises for expected failures.

        Returns {"status": "success" | "already_synced" | "failed", ...}.
        """
        start_time = time.time()
        repo_id: Optional[int] = None
        onedev_repo: Optional[Dict[str, object]] = None

        async with AsyncSessionLocal() as session:
            try:
                # Store webhook event (unique event_id => delivery dedupe).
                try:
                    await WebhookEventCRUD.create(
                        session,
                        event_id=delivery_id,
                        event_type="watch",
                        payload=event.model_dump(mode="json"),
                        signature="verified",
                        delivery_id=delivery_id,
                    )
                    await session.commit()
                except IntegrityError:
                    await session.rollback()
                    logger.warning("Duplicate webhook delivery %s ignored", delivery_id)
                    return {"status": "already_synced", "reason": "duplicate_delivery"}

                repo = await self._resolve_repository(session, event)
                repo_id = int(repo.id)
                if repo.sync_status == "completed":
                    await WebhookEventCRUD.mark_processed(
                        session, delivery_id, repository_id=repo_id
                    )
                    await session.commit()
                    return {
                        "status": "already_synced",
                        "repository_id": repo_id,
                        "onedev_url": repo.onedev_url,
                    }

                onedev_name = self._generate_onedev_name(
                    event.repository.owner.login, event.repository.name
                )
                logger.info(
                    "Starting sync for %s",
                    event.repository.full_name,
                    extra={"repo_id": repo_id},
                )

                # ---- step 1: OneDev project (idempotent get-or-create, retried)
                onedev_repo_dict: Dict[str, object] = await retry_with_backoff(
                    self._create_onedev_repository,
                    event.repository.full_name,
                    onedev_name,
                    max_attempts=settings.max_retries,
                    min_wait=settings.retry_min_wait,
                    max_wait=settings.retry_max_wait,
                    multiplier=settings.retry_backoff_factor,
                    retry_exceptions=(OneDevAPIError,),
                )
                onedev_repo = onedev_repo_dict

                await RepositoryCRUD.update_status(
                    session,
                    repo_id,
                    "cloning",
                    onedev_url=str(onedev_repo["web_url"]),
                    onedev_repo_name=str(onedev_repo["name"]),
                    onedev_project_id=onedev_repo["id"],
                )
                await session.commit()

                # ---- step 2: git clone + push (threaded, retried)
                await retry_with_backoff(
                    self._git_sync,
                    event.repository.clone_url,
                    str(onedev_repo["git_url"]),
                    event.repository.default_branch,
                    max_attempts=settings.max_retries,
                    min_wait=settings.retry_min_wait,
                    max_wait=settings.retry_max_wait,
                    multiplier=settings.retry_backoff_factor,
                    retry_exceptions=(GitOperationError,),
                )

                # ---- success
                duration = int(time.time() - start_time)
                await RepositoryCRUD.update_status(
                    session,
                    repo_id,
                    "completed",
                    last_synced_at=datetime.now(timezone.utc).replace(tzinfo=None),
                )
                await SyncLogCRUD.create(
                    session,
                    repository_id=repo_id,
                    event_type="star",
                    status="success",
                    duration_seconds=duration,
                )
                await WebhookEventCRUD.mark_processed(session, delivery_id, repository_id=repo_id)
                await session.commit()

                logger.info(
                    "Successfully synced %s",
                    event.repository.full_name,
                    extra={
                        "repo_id": repo_id,
                        "onedev_url": onedev_repo["web_url"],
                        "duration": duration,
                    },
                )
                return {
                    "status": "success",
                    "repository_id": repo_id,
                    "onedev_url": onedev_repo["web_url"],
                    "duration_seconds": duration,
                }

            except (OneDevAPIError, GitOperationError) as e:
                return await self._fail(session, event, delivery_id, repo_id, str(e), start_time)

    # ------------------------------------------------------------------ helpers
    async def _resolve_repository(self, session: AsyncSession, event: WatchEvent) -> Repository:
        """Return the Repository row, creating it if absent."""
        repo = await RepositoryCRUD.get_by_github_url(session, event.repository.clone_url)
        if repo:
            logger.info(
                "Repository %s has existing record (status=%s)",
                event.repository.full_name,
                repo.sync_status,
            )
            return repo

        try:
            return await RepositoryCRUD.create(
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
        except IntegrityError:
            # Lost a create race (two deliveries arrived nearly together).
            await session.rollback()
            repo = await RepositoryCRUD.get_by_github_url(session, event.repository.clone_url)
            if repo:
                return repo
            raise

    async def _create_onedev_repository(
        self, full_name: str, onedev_name: str
    ) -> Dict[str, object]:
        """Create (or adopt) the OneDev project for a GitHub repo."""
        return await self.onedev_client.get_or_create_repository(
            name=onedev_name,
            description=f"Synced from GitHub: {full_name}",
        )

    async def _git_sync(self, source_url: str, target_url: str, branch: Optional[str]) -> None:
        """Run the blocking git clone/push in a worker thread.

        Blocking the event loop here would stall every other request (and the
        health endpoint) for the entire sync.
        """
        await asyncio.to_thread(self.git_ops.sync_repository, source_url, target_url, branch)

    async def _fail(
        self,
        session: AsyncSession,
        event: WatchEvent,
        delivery_id: str,
        repo_id: Optional[int],
        error: str,
        start_time: float,
    ) -> Dict[str, object]:
        """Record the failure, mark the webhook processed, return failed."""
        logger.error(
            "Sync failed for %s: %s",
            event.repository.full_name,
            error,
            extra={"repo_id": repo_id},
        )
        try:
            if repo_id:
                await RepositoryCRUD.update_status(session, repo_id, "failed", error_message=error)
                await SyncLogCRUD.create(
                    session,
                    repository_id=repo_id,
                    event_type="star",
                    status="failed",
                    error_message=error,
                    duration_seconds=int(time.time() - start_time),
                )
                await session.commit()
            await WebhookEventCRUD.mark_processed(
                session, delivery_id, repository_id=repo_id, error=error
            )
            await session.commit()
        except Exception:
            logger.exception("Failed to persist sync failure state")
        return {"status": "failed", "repository_id": repo_id, "error": error}

    def _generate_onedev_name(self, owner: str, repo: str) -> str:
        """OneDev project name: {prefix}{owner}-{repo}, lowercased, sanitized."""
        prefix = settings.onedev_repo_prefix
        safe_name = f"{owner}-{repo}".replace(".", "-").replace("_", "-").lower()
        return f"{prefix}{safe_name}"
