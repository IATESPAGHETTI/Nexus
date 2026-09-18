"""Database Agent (Phase 4).

Single responsibility: investigate database health/state via the MCP
`get_database_stats` tool only. Does not touch metrics, logs/traces, or deployments.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

from diagnostic_agent import DiagnosticAgent  # noqa: E402

AGENT_NAME = "database_agent"

INSTRUCTION = (
    "You are the Database Agent for NEXUS, an incident investigation system. "
    "Your only job is to investigate the simulated production database's health "
    "using the get_database_stats tool. Report row counts, status breakdowns, and "
    "recent query performance, and flag anything that looks abnormal, based only "
    "on what the tool returns."
)

DEFAULT_QUESTION = "Check database health: row counts, status breakdown, and recent query performance."

database_agent = DiagnosticAgent(
    agent_name=AGENT_NAME,
    instruction=INSTRUCTION,
    allowed_tools=["get_database_stats"],
    default_question=DEFAULT_QUESTION,
    description="NEXUS diagnostic agent: investigates database health via MCP get_database_stats.",
)


async def investigate(question: str = DEFAULT_QUESTION) -> dict:
    return await database_agent.investigate(question)
