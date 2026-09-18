"""Logs & Traces Agent (Phase 4).

Single responsibility: investigate request logs and distributed traces via the
MCP `query_logs` and `get_trace` tools only. Does not touch metrics, deployments,
or the database.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

from diagnostic_agent import DiagnosticAgent  # noqa: E402

AGENT_NAME = "logs_traces_agent"

INSTRUCTION = (
    "You are the Logs & Traces Agent for NEXUS, an incident investigation system. "
    "Your only job is to investigate request logs and traces for the simulated "
    "production service using the query_logs and get_trace tools. Look for ERROR "
    "level log entries and slow traces, and report what you actually find — do "
    "not speculate about causes outside what the logs/traces show."
)

DEFAULT_QUESTION = "Check recent logs for errors and inspect recent traces for slow requests."

logs_traces_agent = DiagnosticAgent(
    agent_name=AGENT_NAME,
    instruction=INSTRUCTION,
    allowed_tools=["query_logs", "get_trace"],
    default_question=DEFAULT_QUESTION,
    description="NEXUS diagnostic agent: investigates request logs and traces via MCP query_logs/get_trace.",
)


async def investigate(question: str = DEFAULT_QUESTION) -> dict:
    return await logs_traces_agent.investigate(question)
