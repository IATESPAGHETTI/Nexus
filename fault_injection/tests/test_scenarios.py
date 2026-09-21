"""Fast, pure unit tests for fault_injection/scenarios.py -- no network.

Run: python -m pytest fault_injection/tests/test_scenarios.py -q
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "production"))

import pytest  # noqa: E402

import scenarios  # noqa: E402
import state as production_state  # noqa: E402


def test_every_scenario_fault_type_is_a_real_production_fault():
    for scenario in scenarios.SCENARIOS:
        assert scenario["fault_type"] in production_state.FAULT_TYPES


def test_scenarios_cover_all_five_minimum_failure_classes_exactly_once():
    fault_types = [s["fault_type"] for s in scenarios.SCENARIOS]
    assert len(fault_types) == len(production_state.FAULT_TYPES)
    assert set(fault_types) == set(production_state.FAULT_TYPES)


def test_every_scenario_has_the_root_claude_md_section_19_fields():
    required = {
        "scenario_id",
        "description",
        "fault_type",
        "injection_method",
        "expected_symptoms",
        "ground_truth_root_cause",
        "recovery_expectation",
    }
    for scenario in scenarios.SCENARIOS:
        assert required <= set(scenario)


def test_get_ground_truth_exposes_only_scenario_id_and_the_two_ground_truth_fields():
    gt = scenarios.get_ground_truth("FI-bad-deployment")
    assert set(gt) == {"scenario_id", "ground_truth_root_cause", "recovery_expectation"}
    assert gt["ground_truth_root_cause"] == "bad_deployment"


def test_unknown_scenario_id_raises_not_silently_returns_none():
    with pytest.raises(ValueError):
        scenarios.get_scenario("FI-does-not-exist")
