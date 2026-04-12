"""Unit tests for the retry decorator in slayer.llm."""

from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest
from openai import (
    APIConnectionError,
    AuthenticationError,
    InternalServerError,
    RateLimitError,
)

from slayer.llm import retry_on_transient_errors


def _make_request() -> httpx.Request:
    return httpx.Request("POST", "https://api.openai.com/v1/chat/completions")


def _make_response(status: int = 500) -> httpx.Response:
    return httpx.Response(status_code=status, request=_make_request())


class TestRetryOnTransientErrors:
    """Behavioral tests for the retry decorator."""

    def test_succeeds_without_retry(self):
        """Happy path: function returns on first attempt."""
        calls = {"count": 0}

        @retry_on_transient_errors(max_attempts=3)
        def fn():
            calls["count"] += 1
            return "ok"

        assert fn() == "ok"
        assert calls["count"] == 1

    def test_retries_transient_error_then_succeeds(self):
        """Fail twice with APIConnectionError, then succeed on third attempt."""
        calls = {"count": 0}

        @retry_on_transient_errors(max_attempts=3, base_delay=0.0, max_delay=0.0)
        def fn():
            calls["count"] += 1
            if calls["count"] < 3:
                raise APIConnectionError(request=_make_request())
            return "ok"

        with patch("slayer.llm.time.sleep") as mock_sleep:
            assert fn() == "ok"

        assert calls["count"] == 3
        # Slept between retries (attempts 1→2 and 2→3).
        assert mock_sleep.call_count == 2

    def test_raises_after_max_attempts(self):
        """All attempts fail — last exception propagates."""
        calls = {"count": 0}

        @retry_on_transient_errors(max_attempts=3, base_delay=0.0, max_delay=0.0)
        def fn():
            calls["count"] += 1
            raise APIConnectionError(request=_make_request())

        with patch("slayer.llm.time.sleep"):
            with pytest.raises(APIConnectionError):
                fn()

        assert calls["count"] == 3

    def test_rate_limit_error_is_retried(self):
        """RateLimitError is in the retryable set."""
        calls = {"count": 0}

        @retry_on_transient_errors(max_attempts=2, base_delay=0.0)
        def fn():
            calls["count"] += 1
            raise RateLimitError(
                message="rate limited",
                response=_make_response(429),
                body=None,
            )

        with patch("slayer.llm.time.sleep"):
            with pytest.raises(RateLimitError):
                fn()

        assert calls["count"] == 2

    def test_authentication_error_is_not_retried(self):
        """AuthenticationError is permanent — no retry."""
        calls = {"count": 0}

        @retry_on_transient_errors(max_attempts=5, base_delay=0.0)
        def fn():
            calls["count"] += 1
            raise AuthenticationError(
                message="bad key",
                response=_make_response(401),
                body=None,
            )

        with pytest.raises(AuthenticationError):
            fn()

        # Exactly one call — no retry on permanent failure.
        assert calls["count"] == 1

    def test_non_openai_exception_is_not_retried(self):
        """Exceptions outside the retryable set propagate immediately."""
        calls = {"count": 0}

        @retry_on_transient_errors(max_attempts=5, base_delay=0.0)
        def fn():
            calls["count"] += 1
            raise ValueError("not an API error")

        with pytest.raises(ValueError):
            fn()

        assert calls["count"] == 1

    def test_internal_server_error_is_retried(self):
        """5xx APIStatusError subclasses are retryable."""
        calls = {"count": 0}

        @retry_on_transient_errors(max_attempts=3, base_delay=0.0)
        def fn():
            calls["count"] += 1
            raise InternalServerError(
                message="server error",
                response=_make_response(500),
                body=None,
            )

        with patch("slayer.llm.time.sleep"):
            with pytest.raises(InternalServerError):
                fn()

        assert calls["count"] == 3


class TestRetryAsyncSupport:
    """The decorator must retry `async def` functions without blocking the loop."""

    def test_async_function_is_retried(self):
        """An async function's awaited body raises — retries must kick in."""
        import asyncio

        calls = {"count": 0}

        @retry_on_transient_errors(max_attempts=3, base_delay=0.0, max_delay=0.0)
        async def fn():
            calls["count"] += 1
            if calls["count"] < 3:
                raise APIConnectionError(request=_make_request())
            return "ok"

        with patch("slayer.llm.asyncio.sleep") as mock_async_sleep:
            # asyncio.sleep is awaited, so it must return an awaitable.
            async def _noop(*_a, **_kw):
                return None

            mock_async_sleep.side_effect = _noop
            result = asyncio.run(fn())

        assert result == "ok"
        assert calls["count"] == 3
        # Two inter-attempt sleeps (1→2, 2→3), using async sleep — NOT time.sleep.
        assert mock_async_sleep.call_count == 2

    def test_async_function_does_not_use_blocking_sleep(self):
        """Async path must never call the blocking time.sleep."""
        import asyncio

        @retry_on_transient_errors(max_attempts=2, base_delay=0.0)
        async def fn():
            raise APIConnectionError(request=_make_request())

        async def _noop(*_a, **_kw):
            return None

        with patch("slayer.llm.time.sleep") as mock_blocking_sleep, patch(
            "slayer.llm.asyncio.sleep", side_effect=_noop
        ):
            with pytest.raises(APIConnectionError):
                asyncio.run(fn())

        # The blocking sleep must never be touched on the async path.
        assert mock_blocking_sleep.call_count == 0

    def test_async_authentication_error_is_not_retried(self):
        """AuthenticationError on async path must propagate immediately."""
        import asyncio

        calls = {"count": 0}

        @retry_on_transient_errors(max_attempts=5, base_delay=0.0)
        async def fn():
            calls["count"] += 1
            raise AuthenticationError(
                message="bad key",
                response=_make_response(401),
                body=None,
            )

        with pytest.raises(AuthenticationError):
            asyncio.run(fn())

        assert calls["count"] == 1
