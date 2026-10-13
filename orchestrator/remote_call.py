"""Generic single-agent real A2A call helper (Phase 6).

Reused by `orchestrator/investigation.py` for both the Evidence Agent and the
Root-Cause Critic. Uses the exact same `google.adk.agents.RemoteA2aAgent`
client proxy mechanism `orchestrator/incident_manager.py` already uses for the
4 diagnostic agents (agents/tests/test_a2a.py proves a bare `RemoteA2aAgent`
can be run directly through `InMemoryRunner`) -- never a direct Python import
of the target agent's module.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "agents" / "common"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

from remote_agent import build_remote_agent  # noqa: E402
from usage_tracker import take_usage  # noqa: E402


async def call_remote_agent(agent_name: str, description: str, message_text: str) -> dict:
    """Sends `message_text` to `agent_name`'s real A2A service and returns
    `{"response": <parsed JSON or None>, "raw_text": ..., "task_id": ..., "context_id": ...}`.
    """
    remote = build_remote_agent(agent_name, description)
    runner = InMemoryRunner(agent=remote, app_name=f"nexus_call_{agent_name}")
    session = await runner.session_service.create_session(
        app_name=f"nexus_call_{agent_name}", user_id="orchestrator"
    )
    user_message = types.Content(role="user", parts=[types.Part(text=message_text)])

    result_text = None
    task_id = None
    context_id = None
    async for event in runner.run_async(
        user_id="orchestrator", session_id=session.id, new_message=user_message
    ):
        metadata = getattr(event, "custom_metadata", None) or {}
        if metadata.get("a2a:task_id"):
            task_id = metadata["a2a:task_id"]
            context_id = metadata.get("a2a:context_id")
        if not (event.content and event.content.parts):
            continue
        for part in event.content.parts:
            text = getattr(part, "text", None)
            if text:
                result_text = text

    try:
        parsed = json.loads(result_text) if result_text else None
    except json.JSONDecodeError:
        parsed = None

    usage = take_usage(parsed)
    return {"response": parsed, "raw_text": result_text, "task_id": task_id, "context_id": context_id, "llm_usage": usage}
