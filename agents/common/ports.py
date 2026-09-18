"""Single source of truth for each diagnostic agent's A2A service port.

Each of the 4 diagnostic agents runs as its OWN OS process listening on its own
port — genuinely independently addressable, not shared in-process objects.
"""

A2A_HOST = "127.0.0.1"

A2A_PORTS = {
    "metrics_agent": 8101,
    "logs_traces_agent": 8102,
    "change_analysis_agent": 8103,
    "database_agent": 8104,
    # Phase 6: Evidence Agent + Root-Cause Critic, same real-A2A-service pattern.
    "evidence_agent": 8105,
    "root_cause_critic": 8106,
}


def agent_card_url(agent_name: str) -> str:
    port = A2A_PORTS[agent_name]
    return f"http://{A2A_HOST}:{port}/.well-known/agent-card.json"


def base_url(agent_name: str) -> str:
    port = A2A_PORTS[agent_name]
    return f"http://{A2A_HOST}:{port}"
