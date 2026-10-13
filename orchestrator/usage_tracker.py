"""Aggregates the provider-reported token usage each agent returns.

Agents attach `llm_usage` (see agents/common/usage.py) to their A2A result.
This module strips it off, sums it per agent and per incident, and persists the
totals to the incident's `token_usage` field. Nothing is estimated: an agent
that reported no usage simply contributes nothing, and an incident with no
reported usage keeps `token_usage` empty ("Unavailable from provider").
"""

from __future__ import annotations

import event_bridge

_FIELDS = ("llm_calls", "prompt_tokens", "completion_tokens", "total_tokens")
_by_incident: dict[str, dict] = {}


def take_usage(result: dict | None) -> dict | None:
    """Removes and returns `llm_usage` from an agent result dict, if present."""
    if isinstance(result, dict):
        usage = result.pop("llm_usage", None)
        if isinstance(usage, dict):
            return usage
    return None


def record_usage(incident_id: str, agent: str, usage: dict | None) -> None:
    if not usage or not usage.get("total_tokens"):
        return
    state = _by_incident.setdefault(incident_id, {"total": dict.fromkeys(_FIELDS, 0), "by_agent": {}})
    agent_totals = state["by_agent"].setdefault(agent, dict.fromkeys(_FIELDS, 0))
    for field in _FIELDS:
        value = int(usage.get(field) or 0)
        state["total"][field] += value
        agent_totals[field] += value
    event_bridge.update_state(
        incident_id,
        token_usage={"source": "provider-reported via LiteLLM", **state["total"], "by_agent": state["by_agent"]},
    )
