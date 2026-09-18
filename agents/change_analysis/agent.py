"""Change Analysis Agent (Phase 4).

Single responsibility: investigate recent deployments/config changes and the
actual git history behind them via the MCP `get_recent_deployments` and
`get_git_diff` tools only. Does not touch metrics, logs/traces, or the database.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

from diagnostic_agent import DiagnosticAgent  # noqa: E402

AGENT_NAME = "change_analysis_agent"

INSTRUCTION = (
    "You are the Change Analysis Agent for NEXUS, an incident investigation "
    "system. Your only job is to investigate what recently changed in the "
    "simulated production service, using the get_recent_deployments tool (recent "
    "deployment/config history) and the get_git_diff tool (the actual code that "
    "changed). Report which recent change, if any, looks most likely related to "
    "an incident, based only on what those tools return."
)

DEFAULT_QUESTION = "List recent deployments and check whether recent code changes could explain an incident."

change_analysis_agent = DiagnosticAgent(
    agent_name=AGENT_NAME,
    instruction=INSTRUCTION,
    allowed_tools=["get_recent_deployments", "get_git_diff"],
    default_question=DEFAULT_QUESTION,
    description="NEXUS diagnostic agent: investigates recent deployments and git history via MCP get_recent_deployments/get_git_diff.",
)


async def investigate(question: str = DEFAULT_QUESTION) -> dict:
    return await change_analysis_agent.investigate(question)
