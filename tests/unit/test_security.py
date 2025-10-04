"""Unit tests for security module."""

import pytest

from app.core.security import verify_github_signature


class TestGitHubSignatureVerification:
    """Test GitHub webhook signature verification."""

    def test_valid_signature(self):
        """Test valid signature verification."""
        payload = b'{"test": "data"}'
        secret = "test_secret"

        # Calculate expected signature
        import hashlib
        import hmac

        expected_sig = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
        signature_header = f"sha256={expected_sig}"

        # Mock settings
        from app.config import settings

        original_secret = settings.github_webhook_secret
        settings.github_webhook_secret = secret

        try:
            assert verify_github_signature(payload, signature_header) is True
        finally:
            settings.github_webhook_secret = original_secret

    def test_invalid_signature(self):
        """Test invalid signature verification."""
        payload = b'{"test": "data"}'
        signature_header = "sha256=invalid_signature"

        from app.config import settings

        original_secret = settings.github_webhook_secret
        settings.github_webhook_secret = "test_secret"

        try:
            assert verify_github_signature(payload, signature_header) is False
        finally:
            settings.github_webhook_secret = original_secret

    def test_missing_signature(self):
        """Test missing signature header."""
        payload = b'{"test": "data"}'
        assert verify_github_signature(payload, None) is False

    def test_invalid_signature_format(self):
        """Test invalid signature format."""
        payload = b'{"test": "data"}'
        signature_header = "invalid_format"
        assert verify_github_signature(payload, signature_header) is False

