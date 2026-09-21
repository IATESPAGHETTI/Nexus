"""Fast unit tests (Phase 8) for the Recovery Agent's Python-side structural
enforcement -- pure functions, no network, no LLM call. Mirrors
test_evidence_critic.py's approach exactly: proves an invalid/invented action
or risk_level from the model is never trusted.

Run with the isolated agents venv:
    .venv-agents/Scripts/python -m pytest agents/tests/test_recovery.py -q
"""

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

# agents/recovery/agent.py is ALSO literally named "agent.py" -- same module-name
# collision test_evidence_critic.py documents; load by explicit file path.
_recovery_spec = importlib.util.spec_from_file_location(
    "recovery_agent_module", str(Path(__file__).resolve().parents[1] / "recovery" / "agent.py")
)
recovery_agent_module = importlib.util.module_from_spec(_recovery_spec)
_recovery_spec.loader.exec_module(recovery_agent_module)
build_recovery_plan = recovery_agent_module.build_recovery_plan
ACTION_CATALOG = recovery_agent_module.ACTION_CATALOG

SAMPLE_HYPOTHESIS = {"hypothesis_id": "H1", "statement": "bad deployment broke order totals", "confidence": 0.8}
SAMPLE_CRITIQUE = {"critique_id": "crit-1", "hypothesis_id": "H1", "verdict": "SUPPORTED", "rationale": "matches evidence"}


def test_valid_actions_pass_through():
    raw = {
        "actions": [{"action": "rollback_deployment", "params": {"target_version": "1.0.0"}, "rationale": "revert"}],
        "risk_level": "MEDIUM",
        "blast_radius": "single-service",
        "rollback_plan": "redeploy if worse",
    }
    plan = build_recovery_plan(SAMPLE_HYPOTHESIS, SAMPLE_CRITIQUE, raw)
    assert plan["plan_id"].startswith("RP-")
    assert plan["hypothesis_id"] == "H1"
    assert plan["status"] == "PROPOSED"
    assert plan["actions"] == raw["actions"]
    assert plan["dropped_invalid_actions"] == 0


def test_invented_action_is_dropped_not_trusted():
    raw = {
        "actions": [
            {"action": "delete_database", "params": {}, "rationale": "aggressive fix"},
            {"action": "restart_service", "params": {}, "rationale": "safe fix"},
        ],
        "risk_level": "LOW",
        "blast_radius": "n/a",
        "rollback_plan": "n/a",
    }
    plan = build_recovery_plan(SAMPLE_HYPOTHESIS, SAMPLE_CRITIQUE, raw)
    assert len(plan["actions"]) == 1
    assert plan["actions"][0]["action"] == "restart_service"
    assert plan["dropped_invalid_actions"] == 1


def test_invalid_risk_level_falls_back_to_medium():
    raw = {"actions": [], "risk_level": "CATASTROPHIC", "blast_radius": "n/a", "rollback_plan": "n/a"}
    plan = build_recovery_plan(SAMPLE_HYPOTHESIS, SAMPLE_CRITIQUE, raw)
    assert plan["risk_level"] == "MEDIUM"


def test_action_list_capped_at_max_actions():
    raw = {
        "actions": [{"action": name, "params": {}, "rationale": "x"} for name in list(ACTION_CATALOG) * 2],
        "risk_level": "LOW",
        "blast_radius": "n/a",
        "rollback_plan": "n/a",
    }
    plan = build_recovery_plan(SAMPLE_HYPOTHESIS, SAMPLE_CRITIQUE, raw, max_actions=2)
    assert len(plan["actions"]) == 2


def test_non_dict_model_output_yields_empty_actions_not_a_crash():
    plan = build_recovery_plan(SAMPLE_HYPOTHESIS, SAMPLE_CRITIQUE, "not json")
    assert plan["actions"] == []
    assert plan["risk_level"] == "MEDIUM"
    assert plan["status"] == "PROPOSED"


def test_missing_hypothesis_id_is_none_not_fabricated():
    plan = build_recovery_plan({}, {}, {"actions": [], "risk_level": "LOW", "blast_radius": "n/a", "rollback_plan": "n/a"})
    assert plan["hypothesis_id"] is None
