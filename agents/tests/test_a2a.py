"""Real A2A protocol tests (Phase 5).

Requires ALL of the following already running externally (these tests do not
start them — matches the convention used by mcp/tests and
agents/tests/test_agents_integration.py):

  - production/ reachable at PRODUCTION_BASE_URL (default http://localhost:8001)
  - all 4 diagnostic agent A2A services, each its own process:
        .venv-agents/Scripts/python agents/metrics/a2a_service.py
        .venv-agents/Scripts/python agents/logs_traces/a2a_service.py
        .venv-agents/Scripts/python agents/change_analysis/a2a_service.py
        .venv-agents/Scripts/python agents/database/a2a_service.py
  - GROQ_API_KEY (and optionally GROQ_MODEL) in the repo-root .env

Every request here is a REAL HTTP call: fetching a real Agent Card, and sending a
real A2A message via `google.adk.agents.RemoteA2aAgent` to a diagnostic agent
running in its OWN separate OS process (verified with `netstat`/process
inspection during implementation — not an in-process Python call).

Run with the isolated agents venv:
    .venv-agents/Scripts/python -m pytest agents/tests/test_a2a.py -q
"""

import json
import sys
from pathlib import Path

import httpx
import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402

from ports import agent_card_url  # noqa: E402
from remote_agent import build_remote_agent  # noqa: E402

AGENT_TOOL_ALLOWLISTS = {
    "metrics_agent": {"get_metrics"},
    "logs_traces_agent": {"query_logs", "get_trace"},
    "change_analysis_agent": {"get_recent_deployments"},
    "database_agent": {"get_database_stats"},
}


@pytest.mark.parametrize("agent_name", list(AGENT_TOOL_ALLOWLISTS))
def test_agent_card_is_accessible(agent_name):
    # Scoped to the 4 diagnostic agents (each has an MCP tool allowlist to
    # assert against) -- Phase 6 added evidence_agent/root_cause_critic to the
    # same A2A_PORTS registry (agents/common/ports.py) since they're real,
    # independent A2A services too, but they carry no MCP tools, so their
    # Agent Cards are covered by agents/tests/test_evidence_critic.py and the
    # Phase 6 end-to-end test instead.
    response = httpx.get(agent_card_url(agent_name), timeout=5.0)
    assert response.status_code == 200
    card = response.json()
    assert card["name"] == agent_name
    # skills include the model itself plus one entry per allowed MCP tool
    skill_ids = {s["id"] for s in card["skills"]}
    for tool in AGENT_TOOL_ALLOWLISTS[agent_name]:
        assert f"{agent_name}-{tool}" in skill_ids


@pytest_asyncio.fixture(autouse=True)
async def _pace_groq_tpm_limit():
    # Same real Groq free-tier TPM constraint as agents/tests/test_agents_integration.py.
    import asyncio

    yield
    await asyncio.sleep(8)


@pytest.mark.asyncio
async def test_real_a2a_request_reaches_metrics_agent_and_responds():
    remote = build_remote_agent("metrics_agent", "test proxy")
    runner = InMemoryRunner(agent=remote, app_name="nexus_a2a_test")
    session = await runner.session_service.create_session(
        app_name="nexus_a2a_test", user_id="tester"
    )
    user_message = types.Content(
        role="user", parts=[types.Part(text="Summarize current request metrics.")]
    )

    events = []
    async for event in runner.run_async(
        user_id="tester", session_id=session.id, new_message=user_message
    ):
        events.append(event)

    assert events, "expected at least one event back from the remote agent"

    # Protocol-level proof: every event carries real A2A request/response
    # metadata (task_id, context_id) attached by google.adk.agents.RemoteA2aAgent
    # when it actually goes over the wire — this could not appear from a direct
    # in-process Python call.
    final_event = events[-1]
    metadata = final_event.custom_metadata
    assert metadata is not None
    assert metadata.get("a2a:task_id")
    assert metadata.get("a2a:context_id")
    assert final_event.author == "metrics_agent"

    # The task must have genuinely reached TASK_STATE_COMPLETED.
    response_status = metadata["a2a:response"]["status"]
    assert response_status["state"] == "TASK_STATE_COMPLETED"

    # The response text is the real structured Finding built server-side from
    # real MCP evidence (proves MCP still works inside the receiving agent).
    text = final_event.content.parts[0].text
    finding = json.loads(text)
    assert finding["agent"] == "metrics_agent"
    assert finding["evidence"], "expected real MCP evidence in the A2A response"
    for item in finding["evidence"]:
        assert item["tool"] in AGENT_TOOL_ALLOWLISTS["metrics_agent"]
    assert 0.0 <= finding["confidence"] <= 1.0


@pytest.mark.asyncio
async def test_a2a_task_ids_are_unique_per_request():
    remote = build_remote_agent("database_agent", "test proxy")
    runner = InMemoryRunner(agent=remote, app_name="nexus_a2a_test2")

    task_ids = set()
    for _ in range(2):
        session = await runner.session_service.create_session(
            app_name="nexus_a2a_test2", user_id="tester"
        )
        user_message = types.Content(
            role="user", parts=[types.Part(text="Check database health.")]
        )
        last_event = None
        async for event in runner.run_async(
            user_id="tester", session_id=session.id, new_message=user_message
        ):
            last_event = event
        task_ids.add(last_event.custom_metadata["a2a:task_id"])

    assert len(task_ids) == 2, "each real A2A request should get its own task id"
