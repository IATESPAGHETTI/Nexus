"""Local, in-process audit log of every guardrails action -- mirrors
mcp/audit.py's pattern exactly. Not the full NEXUS event bus (that's
orchestrator/event_bridge.py's job, called by orchestrator/recovery.py for
every RECOVERY_*/SAFETY_VALIDATION/HUMAN_APPROVAL_* transition); this is local
auditability of the guardrails layer itself, independent of whether the
backend happens to be reachable.
"""

from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Deque

_lock = Lock()
_entries: Deque[dict] = deque(maxlen=200)


def record(action: str, params: dict, ok: bool, detail: str | None = None) -> None:
    with _lock:
        _entries.append(
            {
                "action": action,
                "params": params,
                "ok": ok,
                "detail": detail,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )


def recent(limit: int = 50) -> list:
    with _lock:
        return list(_entries)[-limit:][::-1]


def clear() -> None:
    with _lock:
        _entries.clear()
