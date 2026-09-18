"""In-memory incident state + event store (Phase 6).

Thread-safe, same ring-buffer-free dict+Lock pattern as
`production/observability.py`. This IS the NEXUS event bus contract from
`docs/EVENT_SCHEMA.md` and the incident-state field set from root CLAUDE.md
section 15 -- not a placeholder. No business logic lives here (backend/CLAUDE.md
"no business logic here beyond persistence/serving"): callers (orchestrator/)
decide what to persist and when; this module only stores and returns it
exactly as given.
"""

from __future__ import annotations

import time
import uuid
from threading import Lock
from typing import Any

_lock = Lock()
_incidents: dict[str, dict[str, Any]] = {}
_events: dict[str, list[dict[str, Any]]] = {}
_event_seq = 0


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def create_incident(description: str) -> dict:
    incident_id = f"INC-{uuid.uuid4().hex[:8]}"
    incident: dict[str, Any] = {
        "incident_id": incident_id,
        "description": description,
        "status": "INVESTIGATING",
        "created_at": _now(),
        "updated_at": _now(),
        "timeline": [],
        "evidence": {},
        "agent_findings": {},
        "agent_messages": {},
        "hypotheses": [],
        "critic_results": [],
        "experiments": [],
        "recovery_plan": None,
        "approval_state": None,
        "action_history": [],
        "token_usage": {},
        "decision": None,
    }
    with _lock:
        _incidents[incident_id] = incident
        _events[incident_id] = []
    return dict(incident)


def get_incident(incident_id: str) -> dict | None:
    with _lock:
        incident = _incidents.get(incident_id)
        return dict(incident) if incident is not None else None


def update_incident(incident_id: str, fields: dict) -> dict | None:
    with _lock:
        incident = _incidents.get(incident_id)
        if incident is None:
            return None
        incident.update(fields)
        incident["updated_at"] = _now()
        return dict(incident)


def append_event(
    incident_id: str,
    event_type: str,
    source: str,
    target: str | None,
    status: str | None,
    payload: dict | None,
) -> dict | None:
    global _event_seq
    with _lock:
        if incident_id not in _incidents:
            return None
        _event_seq += 1
        event = {
            "event_id": f"evt-{_event_seq}",
            "incident_id": incident_id,
            "timestamp": _now(),
            "event_type": event_type,
            "source": source,
            "target": target,
            "status": status,
            "payload": payload or {},
        }
        _events[incident_id].append(event)
        _incidents[incident_id]["timeline"].append(
            {
                "event_id": event["event_id"],
                "timestamp": event["timestamp"],
                "event_type": event_type,
                "source": source,
                "target": target,
            }
        )
        _incidents[incident_id]["updated_at"] = event["timestamp"]
        return dict(event)


def list_events(incident_id: str) -> list[dict] | None:
    with _lock:
        if incident_id not in _incidents:
            return None
        return [dict(e) for e in _events[incident_id]]


def clear() -> None:
    """Test-only reset. Not exposed over HTTP."""
    with _lock:
        _incidents.clear()
        _events.clear()
