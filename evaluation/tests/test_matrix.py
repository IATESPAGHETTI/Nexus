"""Pure tests for evaluation/matrix.py and the healthy-control scoring (no network, no model)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "fault_injection"))
import matrix  # noqa: E402
import scenarios  # noqa: E402
import scoring  # noqa: E402


def test_stdev_and_mean_basics():
    assert matrix.mean([2, 4, 6]) == 4 and matrix.stdev([2, 4, 6]) == pytest.approx(2.0)
    assert matrix.stdev([5]) == 0.0 and matrix.stdev([]) == 0.0


def test_cost_estimate_uses_both_directions_and_overrides():
    assert matrix.estimate_cost_usd(1_000_000, 1_000_000, 0.3, 1.2) == pytest.approx(1.5)
    assert matrix.estimate_cost_usd(2_000_000, 0, 1.0, 9.0) == pytest.approx(2.0)


def test_healthy_control_scoring():
    assert scoring.score_run("unknown", "none", abstained=True)["correct"] is True
    assert scoring.score_run("unknown", "none", abstained=False)["correct"] is True
    wrong = scoring.score_run("db_slowdown", "none", abstained=False)
    assert wrong["false_diagnosis"] is True and wrong["correct"] is False
    # a normal fault run is unchanged
    assert scoring.score_run("db_slowdown", "db_slowdown", False)["correct"] is True


def test_aggregate_reports_controls_separately():
    recs = [
        {**scoring.score_run("db_slowdown", "db_slowdown", False), "latency_seconds": 1},
        {**scoring.score_run("unknown", "none", True), "latency_seconds": 1},
        {**scoring.score_run("config_error", "none", False), "latency_seconds": 1},
    ]
    agg = scoring.aggregate(recs)
    assert agg["root_cause_accuracy"] == 1.0                      # fault runs only
    assert agg["control_runs"] == 2 and agg["control_correct_rate"] == 0.5


def _rec(arm, sid, correct, truth="db_slowdown", predicted="db_slowdown", lat=10, tokens=1000, abstained=False):
    return {"arm": arm, "scenario_id": sid, "ground_truth_root_cause": truth, "predicted_root_cause": predicted,
            "correct": correct, "false_diagnosis": (not correct) and not abstained and predicted != "unknown",
            "abstained": abstained, "latency_seconds": lat,
            "token_cost": {"llm_calls": 9, "prompt_tokens": tokens * 9 // 10, "completion_tokens": tokens // 10, "total_tokens": tokens}}


def test_summarize_arm_separates_faults_from_controls_and_computes_spread():
    recs = [_rec("a", "s1", True, lat=10, tokens=1000), _rec("a", "s1", False, predicted="config_error", lat=30, tokens=3000),
            _rec("a", "c", True, truth="none", predicted="unknown", abstained=True, lat=20, tokens=2000)]
    s = matrix.summarize_arm(recs, 0.3, 1.2)
    assert s["runs"] == 3 and s["fault_runs"] == 2 and s["accuracy"] == 0.5 and s["false_diagnosis_rate"] == 0.5
    assert s["control_runs"] == 1 and s["control_correct_rate"] == 1.0
    assert s["latency_s_mean"] == 20.0 and s["latency_s_std"] == 10.0 and s["tokens_mean"] == 2000
    assert s["est_cost_usd_total"] > 0


def test_summarize_handles_runs_without_token_data():
    r = _rec("b", "s1", True)
    r["token_cost"] = scoring.TOKEN_COST_UNAVAILABLE
    assert matrix.summarize_arm([r])["tokens_mean"] == 0


def test_repeatability():
    recs = [_rec("a", "s1", True), _rec("a", "s1", True), _rec("a", "s2", True), _rec("a", "s2", False, predicted="config_error")]
    assert matrix.repeatability(recs) == {"scenarios_with_repeats": 2, "consistent_fraction": 0.5}
    assert matrix.repeatability([_rec("a", "s1", True)])["consistent_fraction"] is None


def test_arms_group_so_services_restart_only_when_env_differs():
    groups = dict(matrix.group_by_agent_env(matrix.ARMS))
    default = groups[()]
    assert {a.name for a in default} >= {"baseline_single_agent", "hub_default", "hub_no_critic", "blackboard"}
    assert len(groups) == 5  # default, react, fewshot, persona_sre, crewai critic
    assert matrix.ARMS_BY_NAME["blackboard"].run_env_dict() == {"NEXUS_TOPOLOGY": "blackboard"}
    assert matrix.ARMS_BY_NAME["blackboard"].agent_env_dict() == {}   # topology needs no agent restart


def test_markdown_report_prints_numbers_and_every_caveat():
    arms = [matrix.ARMS_BY_NAME["hub_default"]]
    runs = [_rec("hub_default", "FI-db-slowdown", True)]
    report = {"timestamp": "t", "runtime": "deepseek/x", "scenarios": ["FI-db-slowdown"], "repeats": 1, "price_in_per_m": 0.3,
              "price_out_per_m": 1.2, "balance_delta_usd": 0.01, "est_cost_usd_total": 0.0,
              "arms": {"hub_default": matrix.summarize_arm(runs)}, "repeatability": {"hub_default": matrix.repeatability(runs)},
              "arm_definitions": {"hub_default": {"description": "d", "compares": "reference"}}, "runs": runs,
              "caveats": matrix.STANDARD_CAVEATS}
    md = matrix.render_markdown(report)
    assert "| hub_default | 1 | 100% |" in md and "ESTIMATE" in md and "1/1" in md
    assert all(c in md for c in matrix.STANDARD_CAVEATS)


def test_every_benchmark_scenario_has_a_symptom_that_does_not_name_its_cause():
    leaks = ("deployment", "deploy", "config", "dependency", "payment", "fault", "inject", "pool", "database")
    for s in [*scenarios.SCENARIOS, *scenarios.CONTROL_SCENARIOS]:
        text = scenarios.blind_symptom(s["scenario_id"]).lower()
        assert not any(w in text for w in leaks if w not in ("database",)), (s["scenario_id"], text)
    assert scenarios.get_ground_truth("CTRL-healthy")["ground_truth_root_cause"] == "none"
    assert len(scenarios.SCENARIOS) == 5   # control is NOT among the five fault classes


def test_classifier_labels_real_pilot_statements_correctly():
    """Real hypothesis statements produced in the 2026-10-15 pilot (kept as fixtures). The old classifier
    labelled the configuration statements 'db_slowdown' because they mention DB_POOL_SIZE."""
    import json
    fixtures = json.loads((Path(__file__).parent / "real_statements.json").read_text(encoding="utf-8"))
    assert len(fixtures) >= 6
    for f in fixtures:
        assert scoring.classify_statement(f["statement"]) == f["truth"], f["statement"][:120]


def test_classifier_ignores_causes_that_are_only_ruled_out():
    assert scoring.classify_statement("Slow queries on the orders table; no deployment or configuration change explains it.") == "db_slowdown"
    assert scoring.classify_statement("A bad release introduced the errors, not a database problem.") == "bad_deployment"
    assert scoring.classify_statement("payment-service timeouts on order lookups") == "dependency_failure"
    assert scoring.classify_statement("The service is out of memory") == "resource_exhaustion"
    assert scoring.classify_statement("nothing recognisable here") == "unknown" and scoring.classify_statement(None) == "unknown"


def test_rescore_uses_the_current_scorer_on_stored_text():
    import run_matrix
    rec = {"arm": "a", "scenario_id": "s", "status": "DIAGNOSED", "ground_truth_root_cause": "config_error",
           "predicted_statement": "A misconfiguration of DB_POOL_SIZE causes the errors", "predicted_root_cause": "db_slowdown",
           "correct": False, "false_diagnosis": True, "abstained": False}
    out = run_matrix.rescore(rec)
    assert out["predicted_root_cause"] == "config_error" and out["correct"] is True
    abst = {**rec, "status": "ABSTAINED"}
    assert run_matrix.rescore(abst)["predicted_root_cause"] == "unknown"
    base = {"arm": "b", "status": "BASELINE", "correct": True}
    assert run_matrix.rescore(base) == base
