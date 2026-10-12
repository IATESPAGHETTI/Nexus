"""Change Analysis Agent (Phase 4).

Single responsibility: investigate recent deployments/config changes via the MCP
`get_recent_deployments` tool only. (`get_git_diff` was removed from this agent on
2026-10-12: the repo's own history contains the simulator's fault-injection code, which
leaked the answer. The MCP tool still exists but is disabled unless NEXUS_ENABLE_GIT_DIFF=1.)
Does not touch metrics, logs/traces, or the database.
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
    "deployment/config history). Report which recent change, if any, looks most "
    "likely related to an incident, based only on what that tool returns. If no "
    "recent change plausibly explains the symptoms, say so plainly."
)

DEFAULT_QUESTION = "List recent deployments and check whether a recent change could explain an incident."

change_analysis_agent = DiagnosticAgent(
    agent_name=AGENT_NAME,
    instruction=INSTRUCTION,
    allowed_tools=["get_recent_deployments"],
    default_question=DEFAULT_QUESTION,
    description="NEXUS diagnostic agent: investigates recent deployments and config changes via MCP get_recent_deployments.",
)


async def investigate(question: str = DEFAULT_QUESTION) -> dict:
    return await change_analysis_agent.investigate(question)
