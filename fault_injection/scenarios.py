"""Controlled fault scenarios (Phase 9, root CLAUDE.md section 19).

Each scenario's `fault_type` maps 1:1 onto `production/state.py`'s
`FAULT_TYPES` -- the actual mutable flag `injector.py` flips via
`production/service.py`'s `/admin/fault/inject` endpoint (real degraded
behavior, not a fabricated label). `ground_truth_root_cause` and
`recovery_expectation` are the ONLY place this information lives; nothing in
`agents/`, `orchestrator/`, or `guardrails/` ever reads this module (enforced
by dependency isolation -- those packages have no import path to
`fault_injection/`). Only `evaluation/` (scoring, after the fact) is meant to
read `get_ground_truth()`.
"""

from __future__ import annotations

SCENARIOS = [
    {
        "scenario_id": "FI-bad-deployment",
        "blind_symptom": "Orders suddenly started failing with errors for some customers. Investigate the cause.",
        "description": (
            "A new deployment introduces a bug in order total calculation, "
            "causing ~35% of /orders and /orders/{id} requests to fail with a 500."
        ),
        "fault_type": "bad_deployment",
        "injection_method": "POST production/admin/fault/inject {\"fault_type\": \"bad_deployment\"}",
        "expected_symptoms": [
            "elevated 5xx error rate specifically on GET /orders and /orders/{id}",
            "a new deployment entry in /changes at/after the injection time",
            "no db-latency or config-error signal",
        ],
        "ground_truth_root_cause": "bad_deployment",
        "recovery_expectation": "rollback_deployment to the prior known-good version",
    },
    {
        "scenario_id": "FI-db-slowdown",
        "blind_symptom": "Customers report that order requests are responding slowly. Investigate the cause.",
        "description": "The database becomes slow, adding real latency to every query.",
        "fault_type": "db_slowdown",
        "injection_method": "POST production/admin/fault/inject {\"fault_type\": \"db_slowdown\"}",
        "expected_symptoms": [
            "elevated avg_query_ms in /db/diagnostics' query_summary",
            "elevated p99 latency on endpoints that touch the DB (/orders, /orders/{id})",
            "error rate NOT particularly elevated -- this is a latency fault, not an error fault",
        ],
        "ground_truth_root_cause": "db_slowdown",
        "recovery_expectation": "scale_resources (relieve DB-adjacent load) -- no deployment/config change needed",
    },
    {
        "scenario_id": "FI-config-error",
        "blind_symptom": "Every order request is failing with an error right now. Investigate the cause.",
        "description": (
            "A configuration value is invalid (DB_POOL_SIZE=0), causing every "
            "/orders and /orders/{id} request to fail deterministically."
        ),
        "fault_type": "config_error",
        "injection_method": "POST production/admin/fault/inject {\"fault_type\": \"config_error\"}",
        "expected_symptoms": [
            "100% (deterministic, not flaky) error rate on GET /orders and /orders/{id}",
            "log entries containing 'ConfigError: DB_POOL_SIZE'",
            "no new entry in /changes -- distinguishes this from bad_deployment's partial/random errors",
        ],
        "ground_truth_root_cause": "config_error",
        "recovery_expectation": "reset_config",
    },
    {
        "scenario_id": "FI-dependency-failure",
        "blind_symptom": "Looking up a single order takes a long time and then fails. Investigate the cause.",
        "description": "A downstream payment-service dependency becomes unreachable for order-detail lookups.",
        "fault_type": "dependency_failure",
        "injection_method": "POST production/admin/fault/inject {\"fault_type\": \"dependency_failure\"}",
        "expected_symptoms": [
            "elevated latency (~1.5s) and 5xx on GET /orders/{id} specifically, not GET /orders",
            "log entries containing 'DependencyTimeoutError: payment-service unreachable'",
        ],
        "ground_truth_root_cause": "dependency_failure",
        "recovery_expectation": "restart_service",
    },
    {
        "scenario_id": "FI-resource-exhaustion",
        "blind_symptom": "The whole shop is getting slower and sometimes refuses requests. Investigate the cause.",
        "description": "The service runs out of available memory/CPU headroom under load.",
        "fault_type": "resource_exhaustion",
        "injection_method": "POST production/admin/fault/inject {\"fault_type\": \"resource_exhaustion\"}",
        "expected_symptoms": [
            "elevated latency across EVERY endpoint (not just /orders*) -- broad impact distinguishes this from the targeted faults above",
            "log entries containing 'ResourceExhaustedError: memory limit exceeded'",
            "elevated error rate across every endpoint, not just order-related ones",
        ],
        "ground_truth_root_cause": "resource_exhaustion",
        "recovery_expectation": "scale_resources (or restart_service)",
    },
]

# Healthy control (no fault is injected). Ground truth is "none": the correct outcome is to NOT name a cause,
# which is what makes false-diagnosis and abstention-correctness measurable. Kept out of SCENARIOS so the
# "five fault classes" invariant stays true.
CONTROL_SCENARIOS = [
    {
        "scenario_id": "CTRL-healthy",
        "description": "No fault is injected; the shop is healthy.",
        "blind_symptom": "Some customers say the shop might be a little slow today. Investigate the cause.",
        "fault_type": None,
        "injection_method": "none (healthy shop with normal customer traffic)",
        "expected_symptoms": ["normal latency", "no elevated error rate", "no recent bad change"],
        "ground_truth_root_cause": "none",
        "recovery_expectation": "no action needed",
    },
]

SCENARIOS_BY_ID = {s["scenario_id"]: s for s in [*SCENARIOS, *CONTROL_SCENARIOS]}


def blind_symptom(scenario_id: str) -> str:
    """The only text an agent may be given for this scenario: what a customer would notice, never the cause."""
    return get_scenario(scenario_id)["blind_symptom"]


def get_scenario(scenario_id: str) -> dict:
    if scenario_id not in SCENARIOS_BY_ID:
        raise ValueError(f"unknown scenario_id: {scenario_id}")
    return dict(SCENARIOS_BY_ID[scenario_id])


def get_ground_truth(scenario_id: str) -> dict:
    """The ONLY function evaluation/ is meant to call for scoring. Never
    imported by agents/, orchestrator/, or guardrails/."""
    scenario = get_scenario(scenario_id)
    return {
        "scenario_id": scenario_id,
        "ground_truth_root_cause": scenario["ground_truth_root_cause"],
        "recovery_expectation": scenario["recovery_expectation"],
    }
