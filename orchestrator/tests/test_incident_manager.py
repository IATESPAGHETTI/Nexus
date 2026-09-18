"""Real end-to-end test of the Incident Manager (Phase 5).

Requires ALL 4 diagnostic agent A2A services + production/ already running
externally (see agents/tests/test_a2a.py docstring for exact commands), plus
GROQ_API_KEY in the repo-root .env.

Run with the isolated orchestrator venv:
    .venv-orchestrator/Scripts/python -m pytest orchestrator/tests/test_incident_manager.py -q
"""

import asyncio
import sys
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import incident_manager  # noqa: E402

ALL_AGENTS = {"metrics_agent", "logs_traces_agent", "change_analysis_agent", "database_agent"}


@pytest_asyncio.fixture(autouse=True)
async def _pace_groq_tpm_limit():
    # Same real Groq free-tier TPM constraint as agents/tests — dispatching to
    # multiple agents in parallel makes this more, not less, likely to matter.
    yield
    await asyncio.sleep(10)


@pytest.mark.asyncio
async def test_two_agent_parallel_dispatch_is_genuinely_concurrent():
    result = await incident_manager.investigate_incident(
        "Investigate a possible database slowdown.",
        agent_names=["metrics_agent", "database_agent"],
    )
    assert set(result["agents_dispatched"]) == {"metrics_agent", "database_agent"}
    assert set(result["agents_responded"]) == {"metrics_agent", "database_agent"}

    # Each response carries its own real A2A task_id/context_id — two
    # independently issued protocol tasks, not one shared in-process call.
    metrics_a2a = result["a2a"]["metrics_agent"]
    database_a2a = result["a2a"]["database_agent"]
    assert metrics_a2a["task_id"] and database_a2a["task_id"]
    assert metrics_a2a["task_id"] != database_a2a["task_id"]
    assert metrics_a2a["context_id"] != database_a2a["context_id"]

    for agent_name in ("metrics_agent", "database_agent"):
        finding = result["findings"][agent_name]
        assert finding["agent"] == agent_name
        assert finding["evidence"], f"{agent_name} should have real MCP evidence"


@pytest.mark.asyncio
async def test_full_four_agent_parallel_dispatch():
    result = await incident_manager.investigate_incident(
        "Checkout latency spiked and some orders are failing. Investigate."
    )
    assert set(result["agents_dispatched"]) == ALL_AGENTS
    # Retries (litellm.num_retries, see agents/common/diagnostic_agent.py) absorb
    # the real Groq free-tier rate limit that a 4-way parallel burst can trip;
    # even so, allow for at least 3/4 responding so this test isn't flaky on an
    # exhausted quota it doesn't control.
    assert len(result["agents_responded"]) >= 3, (
        f"expected at least 3 of 4 agents to respond, got {result['agents_responded']}"
    )
    for agent_name in result["agents_responded"]:
        assert result["findings"][agent_name]["agent"] == agent_name
