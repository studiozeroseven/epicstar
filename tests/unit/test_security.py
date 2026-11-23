"""Unit tests for webhook signature verification."""

import hashlib
import hmac

from app.core.security import verify_github_signature


def _header(payload: bytes, secret: str = "test_webhook_secret") -> str:
    return "sha256=" + hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


def test_valid_signature():
    payload = b'{"test": "data"}'
    assert verify_github_signature(payload, _header(payload)) is True


def test_invalid_signature():
    payload = b'{"test": "data"}'
    assert verify_github_signature(payload, "sha256=" + "0" * 64) is False


def test_missing_signature():
    assert verify_github_signature(b"{}", None) is False


def test_invalid_signature_format():
    assert verify_github_signature(b"{}", "invalid_format") is False


def test_signature_is_constant_time_comparable():
    # compare_digest would raise on differing lengths; we never hit the
    # raw-compare path with a malformed header.
    assert verify_github_signature(b"{}", "sha256=short") is False


def test_hashlib_hmac_contract():
    # Guard against accidental algorithm drift.
    payload = b"x"
    expected = hmac.new(b"test_webhook_secret", payload, hashlib.sha256).hexdigest()
    assert verify_github_signature(payload, f"sha256={expected}") is True
