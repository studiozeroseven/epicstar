"""Application configuration management."""

from typing import Optional

from pydantic import Field, field_validator
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
    app_version: str = Field(default="0.1.0")
    app_port: int = Field(default=8000)

    # GitHub App
    github_app_id: str = Field(...)
    github_webhook_secret: str = Field(...)
    github_private_key: Optional[str] = Field(default=None)
    github_private_key_path: Optional[str] = Field(default=None)

    # OneDev
    onedev_api_url: str = Field(...)
    onedev_api_token: str = Field(...)
    onedev_repo_prefix: str = Field(default="github-")
    onedev_conflict_strategy: str = Field(default="use_existing")

    # Database
    database_url: str = Field(default="sqlite:///./dev.db")
    database_pool_size: int = Field(default=10)
    database_max_overflow: int = Field(default=20)
    database_pool_recycle: int = Field(default=3600)

    # Git Operations
    git_clone_timeout: int = Field(default=1800)
    git_push_timeout: int = Field(default=1800)
    git_temp_dir: str = Field(default="/tmp/git-sync")
    git_clone_depth: int = Field(default=0)
    git_auth_method: str = Field(default="https")

    # Security
    webhook_rate_limit: int = Field(default=100)
    api_rate_limit: int = Field(default=60)
    cors_enabled: bool = Field(default=False)

    # Retry
    max_retries: int = Field(default=3)
    retry_backoff_factor: int = Field(default=2)
    retry_min_wait: int = Field(default=4)
    retry_max_wait: int = Field(default=60)

    # Monitoring
    prometheus_enabled: bool = Field(default=True)
    prometheus_port: int = Field(default=9090)

    # Logging
    log_format: str = Field(default="json")
    log_file_path: Optional[str] = Field(default=None)

    @field_validator("github_private_key", "github_private_key_path")
    @classmethod
    def validate_github_key(cls, v: Optional[str], info) -> Optional[str]:
        """Validate that at least one GitHub key method is provided."""
        return v

    def get_github_private_key(self) -> str:
        """Get GitHub private key from either inline or file path."""
        if self.github_private_key:
            return self.github_private_key
        if self.github_private_key_path:
            with open(self.github_private_key_path, "r") as f:
                return f.read()
        raise ValueError("Either github_private_key or github_private_key_path must be set")


settings = Settings()

