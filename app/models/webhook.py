"""Pydantic models for GitHub webhooks."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class RepositoryOwner(BaseModel):
    """Repository owner information."""

    login: str
    type: str


class Repository(BaseModel):
    """Repository information from webhook."""

    id: int
    name: str
    full_name: str
    owner: RepositoryOwner
    html_url: str
    clone_url: str
    default_branch: str
    private: bool
    size: int = 0


class Sender(BaseModel):
    """Webhook sender information."""

    login: str


class WatchEvent(BaseModel):
    """GitHub watch (star) event payload."""

    action: str
    starred_at: Optional[datetime] = None
    repository: Repository
    sender: Sender


class WebhookHeaders(BaseModel):
    """GitHub webhook headers."""

    event: str = Field(alias="x-github-event")
    delivery: str = Field(alias="x-github-delivery")
    signature: Optional[str] = Field(default=None, alias="x-hub-signature-256")

    class Config:
        populate_by_name = True

