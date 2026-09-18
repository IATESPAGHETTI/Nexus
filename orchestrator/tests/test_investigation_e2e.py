"""Real end-to-end test of the Phase 6 investigation loop.

Requires ALL of the following already running externally:
  - production/ reachable at PRODUCTION_BASE_URL (default http://localhost:8001)
  - backend/ reachable at NEXUS_BACKEND_URL (default http://localhost:8000)
  - all 6 A2A services, each its own process:
        .venv-agents/Scripts/python agents/metrics/a2a_service.py
        .venv-agents/Scripts/python agents/logs_traces/a2a_service.py
        .venv-agents/Scripts/python agents/change_analysis/a2a_service.py
        .venv-agents/Scripts/python agents/database/a2a_service.py
        .venv-agents/Scripts/python agents/evidence/a2a_service.py
        .venv-agents/Scripts/python agents/critic/a2a_service.py
  - GROQ_API_KEY (and optionally GROQ_MODEL) in the repo-root .env

Proves the full real chain: diagnostic findings (real MCP evidence) -> real A2A
-> Evidence Agent (real A2A, real Groq call) -> Hypotheses -> Root-Cause Critic
(real A2A, real Groq call), bounded re-evaluation loop -> a diagnosis or an
explicit abstention -- with every transition persisted to the real backend
event store (real HTTP, not an in-memory check).

The exact verdict path (SUPPORTED vs. CONTRADICTED vs. ABSTAIN) depends on
live model output and is intentionally NOT asserted here -- see
test_investigation_logic.py for deterministic coverage of every branch. This
test asserts the protocol/architecture guarantees that must hold regardless of
what the model decides.

Run with the isolated orchestrator venv:
    .venv-orchestrator/Scripts/python -m pytest orchestrator/tests/test_investigation_e2e.py -q
"""

import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import event_bridge  # noqa: E402
import investigation  # noqa: E402

VALID_DECISIONS = {"DIAGNOSED", "ABSTAINED"}
VALID_HYPOTHESIS_STATUSES = {
    "PROPOSED", "UNDER_REVIEW", "CHALLENGED", "NEEDS_EVIDENCE",
    "SUPPORTED", "REJECTED", "ABSTAINED",
}


@pytest.mark.asyncio
async def test_real_end_to_end_investigation_reaches_a_bounded_decision():
    result = await investigation.run_investigation(
        "The database appears slow and some orders are failing. Investigate the root cause.",
        agent_names=["metrics_agent", "database_agent"],
        max_loops=2,
    )

    # 1. Real incident state persisted in the real backend.
    assert result["incident_id"].startswith("INC-")
    assert result["status"] in VALID_DECISIONS
    assert result["decision"]["outcome"] == result["status"]
    assert 1 <= result["decision"]["loops_used"] <= 2  # bounded, never exceeds max_loops

    # 2. Real diagnostic findings (real MCP evidence) reached this module only
    # via A2A (agents_findings persisted from orchestrator/incident_manager.py's
    # real RemoteA2aAgent dispatch).
    assert result["agent_findings"], "expected at least one diagnostic agent's real Finding"
    for agent_name, finding in result["agent_findings"].items():
        assert finding["agent"] == agent_name
        assert finding["evidence"], f"{agent_name}'s finding should carry real MCP evidence"

    # 3. Every hypothesis (if any were produced) has a valid, code-assigned
    # shape -- proves the Evidence Agent's structural enforcement ran.
    for hypothesis in result["hypotheses"]:
        assert hypothesis["hypothesis_id"].startswith("H")
        assert hypothesis["status"] in VALID_HYPOTHESIS_STATUSES
        assert 0.0 <= hypothesis["confidence"] <= 1.0
        real_evidence_ids = {
            e["evidence_id"] for f in result["agent_findings"].values() for e in f["evidence"]
        }
        for eid in hypothesis["supporting_evidence_ids"] + hypothesis["contradicting_evidence_ids"]:
            assert eid in real_evidence_ids, "hypothesis must only ever cite real evidence_ids"

    # 4. The Root-Cause Critic actually ran (unless the Evidence Agent produced
    # no hypotheses at all, in which case the loop correctly abstains without
    # ever calling the critic -- see test_investigation_logic.py).
    if result["hypotheses"]:
        assert result["critic_results"], "expected at least one real critic challenge"
        for critique in result["critic_results"]:
            assert critique["verdict"] in {
                "SUPPORTED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE", "REQUEST_MORE_EVIDENCE", "ABSTAIN",
            }

    # 5. The full real event trail exists in the backend event store (this is
    # the Phase 6 event-bridge requirement -- a second, independent real HTTP
    # fetch, not just the return value of run_investigation).
    events = event_bridge.get_events(result["incident_id"])
    event_types = {e["event_type"] for e in events}
    assert "INCIDENT_CREATED" in event_types
    assert "AGENT_STARTED" in event_types
    assert "A2A_MESSAGE_SENT" in event_types
    assert "MCP_TOOL_CALL" in event_types
    assert "EVIDENCE_FOUND" in event_types
    assert "INCIDENT_STATUS_CHANGED" in event_types
    if result["status"] == "ABSTAINED":
        assert "ABSTENTION" in event_types
    else:
        assert "DIAGNOSIS_REACHED" in event_types

    # 6. GROQ_API_KEY is never present in any persisted event payload or state.
    incident_text = httpx.get(f"{event_bridge.BACKEND_URL}/incidents/{result['incident_id']}").text
    assert "GROQ_API_KEY" not in incident_text
    assert "gsk_" not in incident_text
