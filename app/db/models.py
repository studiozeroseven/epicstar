"""SQLAlchemy database models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.database import Base


class Repository(Base):
    """Repository synchronization tracking."""

    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)

    # GitHub information
    github_url = Column(String(500), unique=True, nullable=False, index=True)
    github_repo_name = Column(String(255), nullable=False)
    github_owner = Column(String(255), nullable=False, index=True)
    github_full_name = Column(String(255), nullable=False)
    github_repo_id = Column(Integer, nullable=True)
    github_default_branch = Column(String(100), nullable=True)
    github_is_private = Column(Boolean, default=False)
    github_size_kb = Column(Integer, nullable=True)

    # OneDev information
    onedev_url = Column(String(500), nullable=True)
    onedev_repo_name = Column(String(255), nullable=True)
    onedev_project_id = Column(Integer, nullable=True)

    # Sync status
    sync_status = Column(
        String(50),
        nullable=False,
        default="pending",
        index=True,
    )
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=func.now())
    updated_at = Column(DateTime, nullable=False, default=func.now(), onupdate=func.now())
    last_synced_at = Column(DateTime, nullable=True)
    next_retry_at = Column(DateTime, nullable=True)

    # Metadata
    metadata_json = Column(JSON, nullable=True)


class SyncLog(Base):
    """Audit log for sync operations."""

    __tablename__ = "sync_logs"

    id = Column(Integer, primary_key=True, index=True)
    repository_id = Column(Integer, nullable=False, index=True)

    # Event information
    event_type = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)
    error_message = Column(Text, nullable=True)
    error_code = Column(String(50), nullable=True)

    # Performance metrics
    duration_seconds = Column(Integer, nullable=True)
    bytes_transferred = Column(Integer, nullable=True)

    # Additional context
    payload = Column(JSON, nullable=True)

    # Timestamp
    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)


class WebhookEvent(Base):
    """Raw webhook events for debugging and replay."""

    __tablename__ = "webhook_events"

    id = Column(Integer, primary_key=True, index=True)

    # GitHub webhook information
    event_id = Column(String(100), unique=True, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    delivery_id = Column(String(100), nullable=True)

    # Payload
    payload = Column(JSON, nullable=False)
    signature = Column(String(100), nullable=False)

    # Processing status
    processed = Column(Boolean, default=False, index=True)
    processing_error = Column(Text, nullable=True)

    # Timestamps
    received_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    processed_at = Column(DateTime, nullable=True)

    # Link to repository
    repository_id = Column(Integer, nullable=True)

