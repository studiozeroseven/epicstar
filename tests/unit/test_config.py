"""Unit tests for configuration validation."""

import hashlib
import hmac

import pytest
from pydantic import ValidationError

from app.config import Settings
from app.core.security import verify_github_signature

BASE_KWARGS = dict(
    github_app_id="123",
    github_webhook_secret="secret",
    github_private_key="-----BEGIN KEY-----\nline1\n-----END KEY-----",
    onedev_api_url="https://test.com",
    onedev_username="tester",
    onedev_api_token="token",
)

# Env vars that conftest force-sets; these tests need a clean slate.
TEST_ENV_KEYS = [
    "ENVIRONMENT",
    "GITHUB_APP_ID",
    "GITHUB_WEBHOOK_SECRET",
    "GITHUB_PRIVATE_KEY",
    "GITHUB_PRIVATE_KEY_PATH",
    "ONEDEV_API_URL",
    "ONEDEV_USERNAME",
    "ONEDEV_API_TOKEN",
    "DATABASE_URL",
]


@pytest.fixture
def clean_env(monkeypatch):
    for key in TEST_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)
    yield


def test_default_values(clean_env):
    s = Settings(**BASE_KWARGS, _env_file=None)
    assert s.log_level == "INFO"
    assert s.app_name == "epicstar"
    assert s.app_port == 8000
    assert s.database_url == "sqlite:///./dev.db"
    assert s.onedev_repo_prefix == "github-"
    assert s.onedev_conflict_strategy == "use_existing"
    assert s.prometheus_enabled is True


def test_missing_github_key_source_rejected(clean_env):
    with pytest.raises(ValidationError):
        Settings(
            github_app_id="123",
            github_webhook_secret="secret",
            _env_file=None,
            onedev_api_url="https://test.com",
            onedev_username="tester",
            onedev_api_token="token",
        )


def test_key_path_accepted_without_inline_key(tmp_path, clean_env):
    key_file = tmp_path / "k.pem"
    key_file.write_text("KEYDATA")
    s = Settings(
        **{**BASE_KWARGS, "github_private_key": None},
        github_private_key_path=str(key_file),
        _env_file=None,
    )
    assert s.get_github_private_key() == "KEYDATA"


def test_inline_escaped_newlines_unescaped(clean_env):
    s = Settings(
        **{
            **BASE_KWARGS,
            "github_private_key": "-----BEGIN KEY-----\\nline1\\nline2\\n-----END KEY-----",
        },
        _env_file=None,
    )
    key = s.get_github_private_key()
    assert "\n" in key
    assert "\\n" not in key


def test_required_fields_validation(clean_env):
    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # github_app_id etc. missing


def test_cors_origins_csv_parsing(clean_env):
    s = Settings(
        **BASE_KWARGS,
        _env_file=None,
        cors_origins="http://a.example.com, http://b.example.com",
    )
    assert s.cors_origins == ["http://a.example.com", "http://b.example.com"]


def test_custom_values(clean_env):
    s = Settings(
        **{
            **BASE_KWARGS,
            "environment": "production",
            "log_level": "ERROR",
            "app_port": 9000,
            "database_url": "postgresql://u:p@localhost/db",
        },
        _env_file=None,
    )
    assert s.environment == "production"
    assert s.app_port == 9000
    assert s.database_url == "postgresql://u:p@localhost/db"


def test_secret_used_for_signature_verification_roundtrip():
    # The configured secret must be the one verification uses.
    from app.config import settings as app_settings

    payload = b"roundtrip"
    sig = (
        "sha256="
        + hmac.new(app_settings.github_webhook_secret.encode(), payload, hashlib.sha256).hexdigest()
    )
    assert verify_github_signature(payload, sig) is True
