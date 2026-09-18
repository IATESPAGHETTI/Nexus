"""Local, in-process audit log of MCP tool calls.

Not the full NEXUS event bus (docs/EVENT_SCHEMA.md's MCP_TOOL_CALL/MCP_TOOL_RESULT
events) — that requires the backend event store, which is Phase 6 ("Event Bridge +
Backend") per docs/PROJECT_STATE.md's implementation order. This module exists so
Phase 3 tool calls are still auditable and testable right now: each call records
its name, a bounded summary of its arguments, duration, and outcome. Phase 6 can
read/replace this with the real event bridge without changing the tool layer.
"""

from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Deque

_lock = Lock()
_entries: Deque[dict] = deque(maxlen=200)


def record(tool_name: str, arguments: dict, duration_ms: float, ok: bool, error: str | None = None) -> None:
    with _lock:
        _entries.append(
            {
                "tool": tool_name,
                "arguments": arguments,
                "duration_ms": round(duration_ms, 2),
                "ok": ok,
                "error": error,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )


def recent(limit: int = 50) -> list:
    with _lock:
        return list(_entries)[-limit:][::-1]


def clear() -> None:
    with _lock:
        _entries.clear()
