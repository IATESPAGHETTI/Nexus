"""Static simulated deployment/change history for the production service.

Consumed by the Change Analysis Agent (Phase 4) via the MCP change-history tool
(Phase 3). Fault-injection scenarios (Phase 10) will append to this list to make a
"bad deployment" reachable in the timeline the agents actually query.
"""

CHANGE_HISTORY = [
    {
        "change_id": "chg-001",
        "type": "deployment",
        "version": "1.0.0",
        "deployed_at": "2026-09-10T09:00:00Z",
        "description": "Initial release of nexus-production simulated service.",
        "author": "deepu",
    },
    {
        "change_id": "chg-002",
        "type": "config",
        "version": "1.0.1",
        "deployed_at": "2026-09-14T14:30:00Z",
        "description": "Increased DB connection pool size placeholder for future load.",
        "author": "deepu",
    },
    {
        "change_id": "chg-003",
        "type": "deployment",
        "version": "1.1.0",
        "deployed_at": "2026-09-18T10:00:00Z",
        "description": "Added observability endpoints (metrics/logs/traces/changes/db).",
        "author": "deepu",
    },
]


def recent(limit: int = 20) -> list:
    return sorted(CHANGE_HISTORY, key=lambda c: c["deployed_at"], reverse=True)[:limit]
