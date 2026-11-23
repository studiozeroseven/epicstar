"""Application configuration management.

All values come from environment variables (or a .env file);
see .env.example for the full list.
"""

from pathlib import Path
from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")
    app_name: str = Field(default="epicstar")
    app_version: str = Field(default="0.2.0")
    app_port: int = Field(default=8000)

    # GitHub App
    github_app_id: str = Field(...)
    github_webhook_secret: str = Field(...)
    github_private_key: Optional[str] = Field(default=None)
    github_private_key_path: Optional[str] = Field(default=None)

    # OneDev
    # Server root URL only (no /api or ~api suffix): https://onedev.example.com
    onedev_api_url: str = Field(...)
    # OneDev login name - OneDev authenticates REST + git via USERNAME + access
    # token (HTTP basic). A bearer-only token does NOT work.
    onedev_username: str = Field(...)
    onedev_api_token: str = Field(...)
    onedev_repo_prefix: str = Field(default="github-")
    onedev_conflict_strategy: str = Field(default="use_existing")
    # Optional numeric id of a OneDev parent project to create repos under.
    onedev_project_parent_id: Optional[int] = Field(default=None)

    # Database
    database_url: str = Field(default="sqlite:///./dev.db")
    database_pool_size: int = Field(default=10)  # PostgreSQL only
    database_max_overflow: int = Field(default=20)  # PostgreSQL only
    database_pool_recycle: int = Field(default=3600)  # PostgreSQL only

    # Git Operations (enforced via subprocess timeouts)
    git_clone_timeout: int = Field(default=1800)
    git_push_timeout: int = Field(default=1800)
    git_temp_dir: str = Field(default="/tmp/git-sync")  # nosec B108 - default only
    git_clone_depth: int = Field(default=0)

    # Retry
    max_retries: int = Field(default=3)
    retry_backoff_factor: float = Field(default=2)
    retry_min_wait: float = Field(default=4)
    retry_max_wait: float = Field(default=60)

    # Monitoring
    prometheus_enabled: bool = Field(default=True)

    # Security
    cors_enabled: bool = Field(default=False)
    cors_origins: list[str] = Field(default_factory=list)

    # Logging
    log_format: str = Field(default="json")
    log_file_path: Optional[str] = Field(default=None)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, v):
        """Accept comma-separated values as well as JSON arrays."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @model_validator(mode="after")
    def _require_github_key(self) -> "Settings":
        """Fail fast when neither inline key nor key path is provided."""
        if not self.github_private_key and not self.github_private_key_path:
            raise ValueError("Either github_private_key or github_private_key_path must be set")
        return self

    def get_github_private_key(self) -> str:
        """Get GitHub private key from either inline or file path."""
        if self.github_private_key:
            key = self.github_private_key
        elif self.github_private_key_path:
            key = Path(self.github_private_key_path).read_text()
        else:  # pragma: no cover - guarded by the model validator
            raise ValueError("Either github_private_key or github_private_key_path must be set")
        # Tolerate escaped newlines from env/secret-manager values.
        if "\\n" in key:
            key = key.replace("\\n", "\n")
        return key


settings = Settings()  # type: ignore[call-arg]  # values arrive via env/.env
