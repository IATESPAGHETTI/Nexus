"""Metrics Agent (Phase 4).

Single responsibility: investigate request-rate/latency/error-rate evidence via
the MCP `get_metrics` tool only. Does not touch logs, traces, deployments, or the
database — see agents/logs_traces, agents/change_analysis, agents/database for those.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

from diagnostic_agent import DiagnosticAgent  # noqa: E402

AGENT_NAME = "metrics_agent"

INSTRUCTION = (
    "You are the Metrics Agent for NEXUS, an incident investigation system. Your "
    "only job is to investigate request metrics (counts, error counts, latency) "
    "for the simulated production service using the get_metrics tool. Report "
    "which endpoints look unhealthy (high error rate or high p99 latency) and "
    "which look normal, based only on the numbers the tool returns."
)

DEFAULT_QUESTION = "Summarize current request metrics and flag any unhealthy endpoints."

metrics_agent = DiagnosticAgent(
    agent_name=AGENT_NAME,
    instruction=INSTRUCTION,
    allowed_tools=["get_metrics"],
    default_question=DEFAULT_QUESTION,
    description="NEXUS diagnostic agent: investigates request metrics (counts, error rates, p99 latency) via MCP get_metrics.",
)


async def investigate(question: str = DEFAULT_QUESTION) -> dict:
    return await metrics_agent.investigate(question)
