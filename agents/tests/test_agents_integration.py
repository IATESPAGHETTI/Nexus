"""Real end-to-end integration tests for the 4 Phase 4 diagnostic agents.

Each test makes REAL calls: real Groq/GPT-OSS-120B completion, real MCP protocol
round-trip through a real `mcp/server.py` subprocess, real HTTP calls from that
subprocess to a real running `production/` service. Nothing here is mocked.

Requires:
  - GROQ_API_KEY (and optionally GROQ_MODEL) in the repo-root .env
  - production/ reachable at PRODUCTION_BASE_URL (default http://localhost:8001),
    e.g. `docker compose up -d production` or `uvicorn service:app --port 8001`
  - .venv-mcp/ present with mcp/requirements.txt installed (agents connect to the
    MCP server via that isolated interpreter, per agents/common/mcp_connection.py)

Run with the isolated agents venv:
    .venv-agents/Scripts/python -m pytest agents/tests/test_agents_integration.py -q

Note on pacing: the Groq free-tier limits `openai/gpt-oss-120b` to 8000 tokens/min
(TPM). Running these 5 real-LLM tests back-to-back can burst past that — observed
directly during Phase 4 implementation (2 of 6 tests failed with a genuine
`litellm.RateLimitError` / HTTP 429 from Groq, and passed on retry once the window
reset). This is a real external quota, not a code defect — see
docs/PROJECT_STATE.md "Known Issues". A short pause between tests keeps a normal
`pytest agents/tests` run comfortably under the limit; NEXUS's own application-level
budgets (root CLAUDE.md section 8: MAX_TOKENS_PER_AGENT etc.) are a later phase.
"""

import asyncio
import sys
from pathlib import Path

import pytest
import pytest_asyncio

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

import agents.metrics.agent as metrics_agent_mod  # noqa: E402
import agents.logs_traces.agent as logs_traces_agent_mod  # noqa: E402
import agents.change_analysis.agent as change_analysis_agent_mod  # noqa: E402
import agents.database.agent as database_agent_mod  # noqa: E402


def _assert_valid_finding(finding: dict, agent_name: str, allowed_tools: set[str]):
    assert finding["agent"] == agent_name
    assert finding["source"] == agent_name
    assert finding["finding_id"].startswith("find-")
    assert finding["evidence"], "expected at least one real MCP tool call as evidence"
    for item in finding["evidence"]:
        assert item["tool"] in allowed_tools, f"agent used a tool outside its allowlist: {item['tool']}"
        assert item["evidence_id"].startswith("ev-")
        assert "timestamp" in item
    assert 0.0 <= finding["confidence"] <= 1.0
    assert finding["interpretation"]
    assert "CONFIDENCE" not in finding["interpretation"]
    assert set(finding["window"].keys()) == {"start", "end"}


@pytest_asyncio.fixture(autouse=True)
async def _pace_groq_tpm_limit():
    # See module docstring: Groq's free-tier 8000 TPM limit is real and shared
    # across all agents. Pausing between tests (not within one) keeps a full
    # `pytest agents/tests` run under it without weakening any assertion.
    yield
    await asyncio.sleep(8)


@pytest.mark.asyncio
async def test_metrics_agent_investigates_with_get_metrics_only():
    finding = await metrics_agent_mod.investigate()
    _assert_valid_finding(finding, "metrics_agent", {"get_metrics"})


@pytest.mark.asyncio
async def test_logs_traces_agent_investigates_with_allowed_tools_only():
    finding = await logs_traces_agent_mod.investigate()
    _assert_valid_finding(finding, "logs_traces_agent", {"query_logs", "get_trace"})


@pytest.mark.asyncio
async def test_change_analysis_agent_investigates_with_allowed_tools_only():
    finding = await change_analysis_agent_mod.investigate()
    _assert_valid_finding(
        finding, "change_analysis_agent", {"get_recent_deployments"}
    )


@pytest.mark.asyncio
async def test_database_agent_investigates_with_get_database_stats_only():
    finding = await database_agent_mod.investigate()
    _assert_valid_finding(finding, "database_agent", {"get_database_stats"})


@pytest.mark.asyncio
async def test_database_agent_evidence_reflects_real_seeded_data():
    finding = await database_agent_mod.investigate(
        "How many rows are in the orders table right now?"
    )
    result = finding["evidence"][0]["result"]
    assert result["ok"] is True
    assert result["table_row_counts"]["orders"] == 10
