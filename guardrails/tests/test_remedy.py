"""Tests for guardrails/remedy.py: a plan must be able to fix what the evidence
shows. Pure Python, no network. Evidence items mimic real MCP tool results.

    python -m pytest guardrails/tests/test_remedy.py -q
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import policy  # noqa: E402
import remedy  # noqa: E402

SLOW_DB = {  # shaped like the real get_database_stats result in the failed live run
    "evidence_id": "ev-db1",
    "tool": "get_database_stats",
    "result": {"ok": True, "query_summary": {"avg_query_ms": 209.0, "count": 32}},
}
HEALTHY_DB = {"evidence_id": "ev-db0", "tool": "get_database_stats", "result": {"ok": True, "query_summary": {"avg_query_ms": 0.03}}}
CONFIG_LOG = {"evidence_id": "ev-log1", "tool": "query_logs", "result": {"ok": True, "entries": [{"message": "ConfigError: DB_POOL_SIZE"}]}}


def _plan(action: str, params: dict | None = None) -> dict:
    return {
        "plan_id": "RP-t",
        "actions": [{"action": action, "params": params or {}}],
        "risk_level": "LOW",
        "rollback_plan": "undo",
    }


def test_slow_database_evidence_is_recognised():
    assert remedy.detect_symptoms([SLOW_DB]) == {"db_slowdown": "ev-db1"}
    assert remedy.detect_symptoms([HEALTHY_DB]) == {}


def test_wrong_fix_for_slow_database_is_rejected_and_names_the_right_one():
    result = policy.validate_plan(_plan("reset_config"), evidence_pool=[SLOW_DB])
    assert result["verdict"] == "REJECTED"
    assert any("scale_resources" in r and "db_slowdown" in r for r in result["reasons"])


def test_right_fix_for_slow_database_is_approved_for_human_review():
    result = policy.validate_plan(_plan("scale_resources"), evidence_pool=[SLOW_DB])
    assert result["verdict"] == "APPROVED_FOR_HUMAN_REVIEW"


def test_config_error_marker_needs_reset_config():
    assert policy.validate_plan(_plan("reset_config"), evidence_pool=[CONFIG_LOG])["verdict"] == "APPROVED_FOR_HUMAN_REVIEW"
    assert policy.validate_plan(_plan("scale_resources"), evidence_pool=[CONFIG_LOG])["verdict"] == "REJECTED"


def test_no_recognised_symptom_means_no_opinion():
    # e.g. a bad deployment has no marker here: the check must not block it.
    plan = _plan("rollback_deployment", {"target_version": "1.0.0"})
    assert policy.validate_plan(plan, evidence_pool=[HEALTHY_DB])["verdict"] == "APPROVED_FOR_HUMAN_REVIEW"


def test_without_evidence_the_check_is_skipped():
    assert policy.validate_plan(_plan("reset_config"))["verdict"] == "APPROVED_FOR_HUMAN_REVIEW"
    assert policy.validate_plan(_plan("reset_config"), evidence_pool=[])["verdict"] == "APPROVED_FOR_HUMAN_REVIEW"


def test_any_matching_action_in_a_multi_action_plan_is_enough():
    plan = _plan("reset_config")
    plan["actions"].append({"action": "scale_resources", "params": {}})
    assert policy.validate_plan(plan, evidence_pool=[SLOW_DB])["verdict"] == "APPROVED_FOR_HUMAN_REVIEW"


def test_guidance_lists_the_actions_that_fix_each_symptom():
    guidance = remedy.guidance([SLOW_DB])
    assert guidance == [{"symptom": "db_slowdown", "evidence_id": "ev-db1", "actions_that_address_it": ["scale_resources"]}]


def test_a_diluted_average_does_not_hide_a_slow_database():
    """Real case from the 2026-10-12 live run: the 200-query average was only 57 ms (diluted by earlier fast
    queries), but every RECENT query took ~260 ms."""
    diluted = {
        "evidence_id": "ev-db2",
        "tool": "get_database_stats",
        "result": {
            "ok": True,
            "query_summary": {"total_queries": 200, "avg_query_ms": 57.35},
            "recent_queries": [{"sql": "SELECT * FROM orders ORDER BY id", "duration_ms": ms} for ms in (258.1, 261.4, 263.9, 259.0)],
        },
    }
    assert remedy.detect_symptoms([diluted]) == {"db_slowdown": "ev-db2"}
    assert policy.validate_plan(_plan("restart_service"), evidence_pool=[diluted])["verdict"] == "REJECTED"
    assert policy.validate_plan(_plan("scale_resources"), evidence_pool=[diluted])["verdict"] == "APPROVED_FOR_HUMAN_REVIEW"


def test_a_few_slow_outliers_among_fast_recent_queries_are_not_a_slow_database():
    mostly_fast = {"evidence_id": "ev-x", "tool": "get_database_stats",
                   "result": {"query_summary": {"avg_query_ms": 20.0},
                              "recent_queries": [{"duration_ms": 0.05}, {"duration_ms": 0.04}, {"duration_ms": 0.06}, {"duration_ms": 180.0}]}}
    assert remedy.detect_symptoms([mostly_fast]) == {}
