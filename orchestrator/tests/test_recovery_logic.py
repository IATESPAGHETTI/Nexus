"""Deterministic orchestration-logic tests for the Phase 8 bounded recovery
flow (orchestrator/recovery.py). Same philosophy as
test_investigation_logic.py: exercise the real control-flow code with test
doubles ONLY at its network/execution boundaries --

  - `recovery.call_remote_agent` (real A2A to the Recovery Agent / Metrics
    Agent in production -- not exercised here)
  - `recovery.event_bridge.*` (real HTTP to backend/ in production)
  - `recovery.guardrails_executor.execute_plan` (real HTTP to production/'s
    admin endpoints in production -- guardrails/tests/test_policy_executor.py
    already covers this function's own logic in isolation)
  - `recovery._wait_for_human_approval` (a real human clicking approve/reject
    out-of-band in production; polling loop mechanics themselves are the one
    piece not covered by unit-level tests here -- see the module docstring)

`recovery.guardrails_policy.validate_plan` is deliberately left real (no
monkeypatch) in most tests here -- it's pure, fast, deterministic logic and
exercising the real safety-validation gate is the point of several of these
tests.

Run with the isolated orchestrator venv:
    .venv-orchestrator/Scripts/python -m pytest orchestrator/tests/test_recovery_logic.py -q
"""

import sys
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import event_bridge  # noqa: E402
import recovery  # noqa: E402

HYPOTHESIS = {"hypothesis_id": "H1", "statement": "bad deployment broke order totals", "confidence": 0.85}
CRITIQUE = {"critique_id": "crit-1", "hypothesis_id": "H1", "verdict": "SUPPORTED", "rationale": "matches evidence"}

VALID_PLAN = {
    "plan_id": "RP-abc12345",
    "hypothesis_id": "H1",
    "actions": [{"action": "rollback_deployment", "params": {"target_version": "1.0.0"}, "rationale": "revert"}],
    "risk_level": "MEDIUM",
    "blast_radius": "single-service",
    "rollback_plan": "redeploy 1.1.0 if this makes things worse",
    "status": "PROPOSED",
}


class _FakeBackend:
    def __init__(self):
        self.incident = {"incident_id": "INC-fake", "status": "DIAGNOSED"}
        self.events = []

    def emit_event(self, incident_id, event_type, source, target=None, status=None, payload=None):
        event = {"event_type": event_type, "source": source, "target": target, "status": status, "payload": payload or {}}
        self.events.append(event)
        return event

    def update_state(self, incident_id, **fields):
        self.incident.update(fields)
        return dict(self.incident)

    def get_incident(self, incident_id):
        return dict(self.incident)


@pytest_asyncio.fixture
def fake_backend(monkeypatch):
    backend = _FakeBackend()
    monkeypatch.setattr(event_bridge, "emit_event", backend.emit_event)
    monkeypatch.setattr(event_bridge, "update_state", backend.update_state)
    monkeypatch.setattr(event_bridge, "get_incident", backend.get_incident)
    return backend


def _fake_recovery_agent_call(plan):
    async def _call(agent_name, description, message_text):
        if agent_name == recovery.RECOVERY_AGENT_NAME:
            return {"response": {"recovery_plan": plan}, "task_id": "t1", "context_id": "c1"}
        raise AssertionError(f"unexpected agent call in this test: {agent_name}")

    return _call


@pytest.mark.asyncio
async def test_invalid_plan_is_rejected_by_safety_validation_before_any_approval(fake_backend, monkeypatch):
    bad_plan = dict(VALID_PLAN, actions=[{"action": "delete_database", "params": {}}])
    monkeypatch.setattr(recovery, "call_remote_agent", _fake_recovery_agent_call(bad_plan))

    approval_calls = []
    monkeypatch.setattr(recovery, "_wait_for_human_approval", lambda *a, **k: approval_calls.append(1))

    result = await recovery.run_recovery("INC-fake", HYPOTHESIS, CRITIQUE)

    assert result["outcome"] == "REJECTED_BY_SAFETY_VALIDATION"
    assert approval_calls == []  # never even asked a human
    event_types = [e["event_type"] for e in fake_backend.events]
    assert "SAFETY_VALIDATION" in event_types
    assert "HUMAN_APPROVAL_REQUESTED" not in event_types


@pytest.mark.asyncio
async def test_valid_plan_expires_when_human_never_responds(fake_backend, monkeypatch):
    monkeypatch.setattr(recovery, "call_remote_agent", _fake_recovery_agent_call(dict(VALID_PLAN)))
    monkeypatch.setattr(recovery, "_wait_for_human_approval", lambda incident_id, timeout: {"decision": "EXPIRED"})

    executed = []
    monkeypatch.setattr(recovery.guardrails_executor, "execute_plan", lambda plan: executed.append(plan) or {})

    result = await recovery.run_recovery("INC-fake", HYPOTHESIS, CRITIQUE)

    assert result["outcome"] == "APPROVAL_EXPIRED"
    assert executed == []  # never executes without a real approval
    assert fake_backend.incident["approval_state"]["decision"] == "EXPIRED"


@pytest.mark.asyncio
async def test_human_rejection_stops_before_execution(fake_backend, monkeypatch):
    monkeypatch.setattr(recovery, "call_remote_agent", _fake_recovery_agent_call(dict(VALID_PLAN)))
    monkeypatch.setattr(recovery, "_wait_for_human_approval", lambda incident_id, timeout: {"decision": "REJECTED", "approved_by": "deepu"})

    executed = []
    monkeypatch.setattr(recovery.guardrails_executor, "execute_plan", lambda plan: executed.append(plan) or {})

    result = await recovery.run_recovery("INC-fake", HYPOTHESIS, CRITIQUE)

    assert result["outcome"] == "REJECTED_BY_HUMAN"
    assert executed == []
    event_types = [e["event_type"] for e in fake_backend.events]
    assert "HUMAN_APPROVAL_REJECTED" in event_types
    assert "RECOVERY_EXECUTED" not in event_types


@pytest.mark.asyncio
async def test_approved_plan_executes_then_verifies_and_resolves(fake_backend, monkeypatch):
    async def fake_call_remote_agent(agent_name, description, message_text):
        if agent_name == recovery.RECOVERY_AGENT_NAME:
            return {"response": {"recovery_plan": dict(VALID_PLAN)}, "task_id": "t1", "context_id": "c1"}
        if agent_name == recovery.METRICS_AGENT_NAME:
            return {
                "response": {"evidence": [{"tool": "run_diagnostic", "result": {"error_rate": 0.01}}]},
                "task_id": "t2",
                "context_id": "c2",
            }
        raise AssertionError(f"unexpected agent call: {agent_name}")

    monkeypatch.setattr(recovery, "call_remote_agent", fake_call_remote_agent)
    # verification is decided by the live probe boundary (stubbed healthy here)
    monkeypatch.setattr(recovery, "_probe_service", lambda: {"healthy": True, "per_path": {}})
    monkeypatch.setattr(recovery, "_wait_for_human_approval", lambda incident_id, timeout: {"decision": "APPROVED", "approved_by": "deepu"})

    execution_result = {"plan_id": VALID_PLAN["plan_id"], "action_history": [{"action": "rollback_deployment", "status": "EXECUTED"}], "all_succeeded": True, "kill_switch_engaged": False}
    monkeypatch.setattr(recovery.guardrails_executor, "execute_plan", lambda plan: execution_result)

    result = await recovery.run_recovery("INC-fake", HYPOTHESIS, CRITIQUE)

    assert result["outcome"] == "RESOLVED"
    assert result["verification"]["verified"] is True
    assert fake_backend.incident["status"] == "RESOLVED"
    event_types = [e["event_type"] for e in fake_backend.events]
    assert "RECOVERY_EXECUTED" in event_types
    assert "RECOVERY_VERIFIED" in event_types
    assert "INCIDENT_RESOLVED" in event_types


@pytest.mark.asyncio
async def test_approved_plan_that_fails_execution_never_claims_resolved(fake_backend, monkeypatch):
    async def fake_call_remote_agent(agent_name, description, message_text):
        return {"response": {"recovery_plan": dict(VALID_PLAN)}, "task_id": "t1", "context_id": "c1"}

    monkeypatch.setattr(recovery, "call_remote_agent", fake_call_remote_agent)
    monkeypatch.setattr(recovery, "_wait_for_human_approval", lambda incident_id, timeout: {"decision": "APPROVED", "approved_by": "deepu"})

    execution_result = {"plan_id": VALID_PLAN["plan_id"], "action_history": [{"action": "rollback_deployment", "status": "FAILED"}], "all_succeeded": False, "kill_switch_engaged": False}
    monkeypatch.setattr(recovery.guardrails_executor, "execute_plan", lambda plan: execution_result)

    result = await recovery.run_recovery("INC-fake", HYPOTHESIS, CRITIQUE)

    assert result["outcome"] == "EXECUTION_FAILED"
    assert fake_backend.incident["status"] == "DIAGNOSED"  # never RESOLVED
    event_types = [e["event_type"] for e in fake_backend.events]
    assert "INCIDENT_RESOLVED" not in event_types


@pytest.mark.asyncio
async def test_verification_failure_after_successful_execution_is_not_resolved(fake_backend, monkeypatch):
    async def fake_call_remote_agent(agent_name, description, message_text):
        if agent_name == recovery.RECOVERY_AGENT_NAME:
            return {"response": {"recovery_plan": dict(VALID_PLAN)}, "task_id": "t1", "context_id": "c1"}
        # service still unhealthy after "recovery" -- verification must fail, not be forced.
        return {"response": {"evidence": [{"tool": "run_diagnostic", "result": {"error_rate": 0.9}}]}, "task_id": "t2", "context_id": "c2"}

    monkeypatch.setattr(recovery, "call_remote_agent", fake_call_remote_agent)
    monkeypatch.setattr(recovery, "_probe_service", lambda: {"healthy": False, "per_path": {}})
    monkeypatch.setattr(recovery, "_wait_for_human_approval", lambda incident_id, timeout: {"decision": "APPROVED", "approved_by": "deepu"})

    execution_result = {"plan_id": VALID_PLAN["plan_id"], "action_history": [{"action": "rollback_deployment", "status": "EXECUTED"}], "all_succeeded": True, "kill_switch_engaged": False}
    monkeypatch.setattr(recovery.guardrails_executor, "execute_plan", lambda plan: execution_result)

    result = await recovery.run_recovery("INC-fake", HYPOTHESIS, CRITIQUE)

    assert result["outcome"] == "VERIFICATION_FAILED"
    assert result["verification"]["verified"] is False
    assert fake_backend.incident["status"] == "DIAGNOSED"
