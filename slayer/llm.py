"""Shared LLM provider module.

All agents and pipelines route LLM calls through this module.
The LLMProvider Protocol pattern makes it easy to swap implementations.

Example:
    from slayer.llm import get_default_provider
    provider = get_default_provider()
    result = provider.generate_json(prompt)
"""

from __future__ import annotations

import logging
import os
import random
import time
from functools import wraps
from typing import Callable, Optional, Protocol, runtime_checkable

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    OpenAI,
    RateLimitError,
)

from slayer.config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# config.py declares OPENAI_MODEL but we allow environment override here
# so jobs can switch models without touching source.
LLM_MODEL = os.environ.get("SLAYER_LLM_MODEL", "gpt-4o-mini")


# Transient network/timeout errors that are always worth retrying.
# APIStatusError subclasses (Auth, BadRequest, RateLimit, InternalServer, ...)
# are filtered by HTTP status code inside the decorator — only 5xx and 429
# are retried. 4xx permanent failures (401, 400, 403, 404) are NOT retried.
_RETRYABLE_NETWORK_ERRORS: tuple[type[Exception], ...] = (
    APIConnectionError,
    APITimeoutError,
)


def _is_retryable_status(exc: Exception) -> bool:
    """Return True if the exception carries a retryable HTTP status (5xx or 429)."""
    if isinstance(exc, RateLimitError):
        return True
    if isinstance(exc, APIStatusError):
        status = getattr(exc, "status_code", None)
        if isinstance(status, int) and 500 <= status < 600:
            return True
    return False


def retry_on_transient_errors(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
) -> Callable:
    """Retry decorator with exponential backoff + jitter for transient OpenAI errors.

    Retries on:
      - APIConnectionError / APITimeoutError (network-level)
      - RateLimitError (429)
      - APIStatusError subclasses with 5xx status (server error)

    Does NOT retry on:
      - AuthenticationError (401)
      - BadRequestError (400)
      - PermissionDeniedError (403)
      - NotFoundError (404)
      - Any non-OpenAI exception

    Args:
        max_attempts: Maximum number of attempts including the first call.
        base_delay: Base delay in seconds for the first retry.
        max_delay: Upper bound on any single delay.
    """

    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc: Optional[Exception] = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except _RETRYABLE_NETWORK_ERRORS as e:
                    last_exc = e
                    # Always retry pure network / timeout errors.
                except APIStatusError as e:
                    if not _is_retryable_status(e):
                        # Permanent 4xx — propagate without retry.
                        raise
                    last_exc = e

                if attempt == max_attempts:
                    logger.error(
                        "LLM call failed after %d attempts: %s", attempt, last_exc
                    )
                    raise last_exc  # type: ignore[misc]
                delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                delay += random.uniform(0, delay * 0.1)
                logger.warning(
                    "LLM call attempt %d failed (%s); retrying in %.1fs",
                    attempt,
                    type(last_exc).__name__,
                    delay,
                )
                time.sleep(delay)
            # Unreachable — either we returned or raised above.
            if last_exc is not None:
                raise last_exc
            raise RuntimeError("retry_on_transient_errors: unexpected exit")

        return wrapper

    return decorator


@runtime_checkable
class LLMProvider(Protocol):
    """Common interface for LLM providers that return JSON."""

    def generate_json(self, prompt: str, system_message: str | None = None) -> str:
        """Send the prompt and return a JSON string response."""
        ...


class OpenAIProvider:
    """OpenAI API backed LLM provider."""

    def __init__(self, model: str | None = None, api_key: str | None = None):
        key = api_key or OPENAI_API_KEY
        if not key:
            raise ValueError("OPENAI_API_KEY is not set")
        self.client = OpenAI(api_key=key)
        self.model = model or LLM_MODEL

    @retry_on_transient_errors(max_attempts=3)
    def generate_json(self, prompt: str, system_message: str | None = None) -> str:
        """Send the prompt and return a JSON string response."""
        messages: list[dict[str, str]] = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})

        logger.debug("LLM call (model=%s)", self.model)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or "{}"
        logger.debug("LLM response received (%d chars)", len(content))
        return content


def get_default_provider() -> OpenAIProvider:
    """Return the default LLM provider instance."""
    return OpenAIProvider()


def get_chat_model(model: str = "gpt-4o-mini"):
    """Return a ChatOpenAI instance for LangGraph create_react_agent.

    `max_retries=3` enables ChatOpenAI's built-in transient error retry for
    the LangChain code path, mirroring the custom retry used by OpenAIProvider.
    """
    from langchain_openai import ChatOpenAI

    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY is not set")
    return ChatOpenAI(model=model, api_key=OPENAI_API_KEY, max_retries=3)


def parse_agent_json(content: str) -> str:
    """Extract a JSON string from an LLM agent response.

    Handles three forms: fenced ```json blocks, raw JSON starting with `{`,
    and JSON embedded in surrounding text. Raises ValueError if no JSON
    object can be located.
    """
    if not content or not isinstance(content, str):
        raise ValueError("Empty or non-string content")
    content = content.strip()
    # Try fenced ```json block first.
    if "```json" in content:
        parts = content.split("```json")
        if len(parts) >= 2:
            json_part = parts[1].split("```")[0].strip()
            if json_part:
                return json_part
    # Try generic ``` fenced block.
    if "```" in content:
        parts = content.split("```")
        if len(parts) >= 3:
            json_part = parts[1].strip()
            if json_part.startswith("{"):
                return json_part
    # Try raw JSON that starts with `{`.
    if content.startswith("{"):
        return content
    # Try finding JSON embedded in surrounding text.
    if "{" not in content or "}" not in content:
        raise ValueError("No JSON object found in response")
    try:
        start = content.index("{")
        end = content.rindex("}") + 1
        return content[start:end]
    except ValueError:
        raise ValueError("Failed to extract JSON boundaries")
