"""Unit tests for retry helpers."""

import pytest

from app.core.retry import retry_with_backoff
from app.utils.exceptions import RetryableError


async def test_retry_succeeds_after_transient_failures():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RetryableError("transient")
        return "ok"

    result = await retry_with_backoff(
        flaky, max_attempts=5, min_wait=0.01, max_wait=0.02, multiplier=1
    )
    assert result == "ok"
    assert calls["n"] == 3


async def test_retry_exhaustion_raises_last_error():
    calls = {"n": 0}

    async def always_fails():
        calls["n"] += 1
        raise RetryableError(f"attempt {calls['n']}")

    with pytest.raises(RetryableError, match="attempt 3"):
        await retry_with_backoff(
            always_fails, max_attempts=3, min_wait=0.01, max_wait=0.02, multiplier=1
        )
    assert calls["n"] == 3


async def test_non_retryable_exception_propagates_immediately():
    calls = {"n": 0}

    async def no_retry():
        calls["n"] += 1
        raise ValueError("unexpected")

    with pytest.raises(ValueError):
        await retry_with_backoff(
            no_retry, max_attempts=3, min_wait=0.01, max_wait=0.02, multiplier=1
        )
    assert calls["n"] == 1


async def test_kwargs_passthrough():
    calls: dict = {}

    async def takes_kwargs(a, b=None):
        calls["args"] = (a, b)
        return a

    result = await retry_with_backoff(
        takes_kwargs, 1, b=2, max_attempts=2, min_wait=0.01, max_wait=0.02, multiplier=1
    )
    assert result == 1
    assert calls["args"] == (1, 2)
