"""Fast, deterministic unit tests for guardrails/policy.py and
guardrails/executor.py -- no network, no LLM. production_client.post/get is
monkeypatched at its own module boundary (the same style
orchestrator/tests/test_investigation_logic.py uses for its network
boundaries) so these run in well under a second.

Run (any venv with httpx + pytest -- orchestrator's or a plain one):
    python -m pytest guardrails/tests -q
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

import executor  # noqa: E402
import kill_switch  # noqa: E402
import policy  # noqa: E402
from config import ALLOWED_ACTIONS  # noqa: E402


def _valid_plan(**overrides) -> dict:
    plan = {
        "plan_id": "RP-test1234",
        "hypothesis_id": "H1",
        "actions": [{"action": "rollback_deployment", "params": {"target_version": "1.0.0"}, "rationale": "revert bad deploy"}],
        "risk_level": "MEDIUM",
        "blast_radius": "single-service",
        "rollback_plan": "redeploy 1.1.0 if this makes things worse",
        "status": "PROPOSED",
    }
    plan.update(overrides)
    return plan


# --- policy.validate_plan --------------------------------------------------


def test_valid_plan_is_approved_for_human_review():
    result = policy.validate_plan(_valid_plan())
    assert result["verdict"] == "APPROVED_FOR_HUMAN_REVIEW"
    assert result["reasons"] == []
    assert result["checked_actions"] == ["rollback_deployment"]


def test_unknown_action_is_rejected():
    plan = _valid_plan(actions=[{"action": "delete_database", "params": {}}])
    result = policy.validate_plan(plan)
    assert result["verdict"] == "REJECTED"
    assert any("delete_database" in r for r in result["reasons"])


def test_missing_required_param_is_rejected():
    plan = _valid_plan(actions=[{"action": "rollback_deployment", "params": {}}])
    result = policy.validate_plan(plan)
    assert result["verdict"] == "REJECTED"
    assert any("missing required params" in r for r in result["reasons"])


def test_too_many_actions_is_rejected():
    action = {"action": "restart_service", "params": {}}
    plan = _valid_plan(actions=[action, action, action, action])
    result = policy.validate_plan(plan)
    assert result["verdict"] == "REJECTED"
    assert any("MAX_ACTIONS_PER_PLAN" in r for r in result["reasons"])


def test_high_risk_is_rejected():
    plan = _valid_plan(risk_level="HIGH")
    result = policy.validate_plan(plan)
    assert result["verdict"] == "REJECTED"
    assert any("risk_level" in r for r in result["reasons"])


def test_missing_rollback_plan_is_rejected():
    plan = _valid_plan(rollback_plan="")
    result = policy.validate_plan(plan)
    assert result["verdict"] == "REJECTED"
    assert any("rollback_plan" in r for r in result["reasons"])


def test_no_actions_is_rejected():
    plan = _valid_plan(actions=[])
    result = policy.validate_plan(plan)
    assert result["verdict"] == "REJECTED"
    assert any("no actions" in r for r in result["reasons"])


def test_all_allowed_actions_have_a_spec_with_addresses_faults():
    for name, spec in ALLOWED_ACTIONS.items():
        assert "endpoint" in spec
        assert "required_params" in spec
        assert spec["risk_level"] in ("LOW", "MEDIUM", "HIGH")
        assert spec["addresses_faults"]


# --- executor.execute_plan --------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_kill_switch():
    kill_switch.disengage()
    yield
    kill_switch.disengage()


def test_execute_plan_runs_actions_in_order(monkeypatch):
    calls = []

    def fake_post(path, json=None):
        calls.append((path, json))
        return {"deployed_version": json.get("target_version", "unknown")}

    monkeypatch.setattr("executor.production_client.post", fake_post)
    plan = _valid_plan()
    result = executor.execute_plan(plan)

    assert result["all_succeeded"] is True
    assert result["kill_switch_engaged"] is False
    assert len(result["action_history"]) == 1
    assert result["action_history"][0]["status"] == "EXECUTED"
    assert calls == [("/admin/recovery/rollback_deployment", {"target_version": "1.0.0"})]


def test_execute_plan_drops_unexpected_params_before_calling_production(monkeypatch):
    calls = []
    monkeypatch.setattr("executor.production_client.post", lambda path, json=None: calls.append(json) or {})
    plan = _valid_plan(
        actions=[{"action": "restart_service", "params": {"unexpected": "value"}}]
    )
    executor.execute_plan(plan)
    assert calls == [{}]  # restart_service has no required_params -- extra key never forwarded


def test_execute_plan_stops_on_kill_switch(monkeypatch):
    calls = []
    monkeypatch.setattr("executor.production_client.post", lambda path, json=None: calls.append(path) or {})
    kill_switch.engage("test")
    plan = _valid_plan()
    result = executor.execute_plan(plan)

    assert result["kill_switch_engaged"] is True
    assert result["all_succeeded"] is False
    assert result["action_history"][0]["status"] == "SKIPPED_KILL_SWITCH"
    assert calls == []  # production_client.post never called


def test_execute_plan_stops_on_first_failure_not_all_or_nothing(monkeypatch):
    calls = []

    def fake_post(path, json=None):
        calls.append(path)
        raise executor.production_client.ProductionUnavailableError("boom")

    monkeypatch.setattr("executor.production_client.post", fake_post)
    plan = _valid_plan(
        actions=[
            {"action": "restart_service", "params": {}},
            {"action": "reset_config", "params": {}},
        ]
    )
    result = executor.execute_plan(plan)

    assert result["all_succeeded"] is False
    assert len(calls) == 1  # second action never attempted
    assert result["action_history"][0]["status"] == "FAILED"


def test_execute_plan_refuses_action_not_in_allowlist_even_if_it_slipped_through():
    plan = _valid_plan(actions=[{"action": "shell_exec", "params": {"cmd": "rm -rf /"}}])
    result = executor.execute_plan(plan)
    assert result["all_succeeded"] is False
    assert result["action_history"][0]["status"] == "FAILED"


# --- kill_switch -------------------------------------------------------------


def test_kill_switch_engage_disengage_roundtrip():
    assert kill_switch.is_engaged() is False
    kill_switch.engage("manual test")
    assert kill_switch.is_engaged() is True
    kill_switch.disengage()
    assert kill_switch.is_engaged() is False
