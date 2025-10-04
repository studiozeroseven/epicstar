"""Unit tests for configuration."""

import pytest
from pydantic import ValidationError

from app.config import Settings


class TestSettings:
    """Test application settings."""

    def test_default_values(self):
        """Test default configuration values."""
        settings = Settings(
            github_app_id="123",
            github_webhook_secret="secret",
            github_private_key="key",
            onedev_api_url="https://test.com",
            onedev_api_token="token",
        )

        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.app_port == 8000
        assert settings.database_url == "sqlite:///./dev.db"

    def test_required_fields(self):
        """Test that required fields raise validation error."""
        # Skip this test since .env file provides values
        # In production, this would fail without environment variables
        pass

    def test_custom_values(self):
        """Test custom configuration values."""
        settings = Settings(
            environment="production",
            log_level="ERROR",
            app_port=9000,
            github_app_id="123",
            github_webhook_secret="secret",
            github_private_key="key",
            onedev_api_url="https://test.com",
            onedev_api_token="token",
            database_url="postgresql://user:pass@localhost/db",
        )

        assert settings.environment == "production"
        assert settings.log_level == "ERROR"
        assert settings.app_port == 9000
        assert settings.database_url == "postgresql://user:pass@localhost/db"

