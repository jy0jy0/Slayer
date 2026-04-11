"""Streaming event types emitted by agents to UI callbacks.

Using `str`-Enum so legacy comparisons like `event_type == "thinking"`
continue to work during incremental migration from magic strings.
"""

from __future__ import annotations

from enum import Enum


class EventType(str, Enum):
    """Agent → UI streaming event kinds.

    Each member is also a plain string equal to its value, so
    `EventType.THINKING == "thinking"` evaluates True and the enum
    can be used as a dict key interchangeably with the raw string.
    """

    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    DONE = "done"
