"""Incident Manager (Phase 5): dispatches an incident to all 4 diagnostic agents
in parallel over real A2A, and collects their structured Findings.

```
Incident
   |
Incident Manager (this module, ADK ParallelAgent of 4 RemoteA2aAgent proxies)
   |
   +-- A2A --> Metrics Agent service (agents/metrics/a2a_service.py, its own process)
   +-- A2A --> Logs & Traces Agent service (its own process)
   +-- A2A --> Change Analysis Agent service (its own process)
   +-- A2A --> Database Agent service (its own process)
   |
structured findings (parsed from each agent's real A2A response)
```

Every diagnostic agent must already be running as its own `a2a_service.py` process
(see agents/common/ports.py for ports) before calling `investigate_incident()`.
This module makes no MCP or production/ calls itself — it only ever reaches the
diagnostic agents through the real A2A protocol (`google.adk.agents.RemoteA2aAgent`),
matching root CLAUDE.md section 10 ("do not claim genuine A2A merely because
separate ADK agent objects exist in the same Python process" — here they do NOT;
each `RemoteA2aAgent` proxy is a client for an agent running in its own process).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "agents" / "common"))

from google.adk.agents import ParallelAgent  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

from remote_agent import build_remote_agent  # noqa: E402

DIAGNOSTIC_AGENTS = {
    "metrics_agent": "Investigates request metrics via MCP get_metrics.",
    "logs_traces_agent": "Investigates logs and traces via MCP query_logs/get_trace.",
    "change_analysis_agent": (
        "Investigates deployments/git history via MCP get_recent_deployments/get_git_diff."
    ),
    "database_agent": "Investigates database health via MCP get_database_stats.",
}


def build_incident_manager(agent_names: list[str] | None = None) -> ParallelAgent:
    names = agent_names or list(DIAGNOSTIC_AGENTS)
    sub_agents = [build_remote_agent(name, DIAGNOSTIC_AGENTS[name]) for name in names]
    return ParallelAgent(name="incident_manager", sub_agents=sub_agents)


async def investigate_incident(
    incident_description: str, agent_names: list[str] | None = None
) -> dict:
    """Dispatches `incident_description` to the named diagnostic agents (all 4 by
    default) in parallel over real A2A and returns their structured Findings.
    """
    manager = build_incident_manager(agent_names)
    runner = InMemoryRunner(agent=manager, app_name="nexus_incident")
    session = await runner.session_service.create_session(
        app_name="nexus_incident", user_id="incident_manager"
    )

    user_message = types.Content(
        role="user", parts=[types.Part(text=incident_description)]
    )

    findings_by_agent: dict[str, dict] = {}
    a2a_by_agent: dict[str, dict] = {}

    async for event in runner.run_async(
        user_id="incident_manager",
        session_id=session.id,
        new_message=user_message,
    ):
        if not (event.content and event.content.parts):
            continue
        metadata = getattr(event, "custom_metadata", None) or {}
        for part in event.content.parts:
            text = getattr(part, "text", None)
            if not text:
                continue
            try:
                finding = json.loads(text)
            except json.JSONDecodeError:
                continue
            if isinstance(finding, dict) and "finding_id" in finding:
                findings_by_agent[event.author] = finding
                a2a_by_agent[event.author] = {
                    "task_id": metadata.get("a2a:task_id"),
                    "context_id": metadata.get("a2a:context_id"),
                }

    return {
        "incident_description": incident_description,
        "findings": findings_by_agent,
        "a2a": a2a_by_agent,
        "agents_dispatched": agent_names or list(DIAGNOSTIC_AGENTS),
        "agents_responded": list(findings_by_agent.keys()),
    }
