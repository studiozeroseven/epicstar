"""CRUD operations for database models."""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import Repository, SyncLog, WebhookEvent

logger = get_logger(__name__)


class RepositoryCRUD:
    """CRUD operations for Repository model."""

    @staticmethod
    async def create(
        session: AsyncSession,
        github_url: str,
        github_repo_name: str,
        github_owner: str,
        github_full_name: str,
        **kwargs,
    ) -> Repository:
        """Create a new repository record."""
        repo = Repository(
            github_url=github_url,
            github_repo_name=github_repo_name,
            github_owner=github_owner,
            github_full_name=github_full_name,
            **kwargs,
        )
        session.add(repo)
        await session.flush()
        await session.refresh(repo)
        logger.info(f"Created repository record: {github_full_name}")
        return repo

    @staticmethod
    async def get_by_github_url(session: AsyncSession, github_url: str) -> Optional[Repository]:
        """Get repository by GitHub URL."""
        result = await session.execute(select(Repository).where(Repository.github_url == github_url))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_id(session: AsyncSession, repo_id: int) -> Optional[Repository]:
        """Get repository by ID."""
        result = await session.execute(select(Repository).where(Repository.id == repo_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update_status(
        session: AsyncSession,
        repo_id: int,
        status: str,
        error_message: Optional[str] = None,
        **kwargs,
    ) -> Optional[Repository]:
        """Update repository sync status."""
        repo = await RepositoryCRUD.get_by_id(session, repo_id)
        if repo:
            repo.sync_status = status
            repo.error_message = error_message
            repo.updated_at = datetime.utcnow()

            for key, value in kwargs.items():
                if hasattr(repo, key):
                    setattr(repo, key, value)

            await session.flush()
            await session.refresh(repo)
            logger.info(f"Updated repository {repo_id} status to {status}")
        return repo

    @staticmethod
    async def increment_retry(session: AsyncSession, repo_id: int) -> Optional[Repository]:
        """Increment retry count."""
        repo = await RepositoryCRUD.get_by_id(session, repo_id)
        if repo:
            repo.retry_count += 1
            repo.updated_at = datetime.utcnow()
            await session.flush()
            await session.refresh(repo)
        return repo


class SyncLogCRUD:
    """CRUD operations for SyncLog model."""

    @staticmethod
    async def create(
        session: AsyncSession,
        repository_id: int,
        event_type: str,
        status: str,
        **kwargs,
    ) -> SyncLog:
        """Create a sync log entry."""
        log = SyncLog(
            repository_id=repository_id,
            event_type=event_type,
            status=status,
            **kwargs,
        )
        session.add(log)
        await session.flush()
        await session.refresh(log)
        return log

    @staticmethod
    async def get_by_repository(
        session: AsyncSession, repository_id: int, limit: int = 50
    ) -> List[SyncLog]:
        """Get sync logs for a repository."""
        result = await session.execute(
            select(SyncLog)
            .where(SyncLog.repository_id == repository_id)
            .order_by(SyncLog.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())


class WebhookEventCRUD:
    """CRUD operations for WebhookEvent model."""

    @staticmethod
    async def create(
        session: AsyncSession,
        event_id: str,
        event_type: str,
        payload: Dict,
        signature: str,
        **kwargs,
    ) -> WebhookEvent:
        """Create a webhook event record."""
        event = WebhookEvent(
            event_id=event_id,
            event_type=event_type,
            payload=payload,
            signature=signature,
            **kwargs,
        )
        session.add(event)
        await session.flush()
        await session.refresh(event)
        return event

    @staticmethod
    async def mark_processed(
        session: AsyncSession,
        event_id: str,
        repository_id: Optional[int] = None,
        error: Optional[str] = None,
    ) -> Optional[WebhookEvent]:
        """Mark webhook event as processed."""
        result = await session.execute(
            select(WebhookEvent).where(WebhookEvent.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        if event:
            event.processed = True
            event.processed_at = datetime.utcnow()
            event.repository_id = repository_id
            event.processing_error = error
            await session.flush()
            await session.refresh(event)
        return event

