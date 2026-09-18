"""Builds ADK `RemoteA2aAgent` proxies for the 4 diagnostic A2A services.

A `RemoteA2aAgent` is ADK's real A2A client wrapper: calling/invoking it performs
an actual HTTP request to the target service's A2A JSON-RPC endpoint (resolved
from its Agent Card) and translates the real task response back into ADK Events.
This is what the Incident Manager uses to reach each diagnostic agent — genuine
network calls to independently running processes, never a direct Python call into
another agent's code.
"""

from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

from ports import agent_card_url


def build_remote_agent(agent_name: str, description: str) -> RemoteA2aAgent:
    return RemoteA2aAgent(
        name=agent_name,
        agent_card=agent_card_url(agent_name),
        description=description,
    )
