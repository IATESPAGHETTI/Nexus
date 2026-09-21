# Fault Injection Local Instructions

## Purpose
Benchmark/fault scenarios injected into `production/` for blind evaluation.
Vanshika's workstream on paper (implemented by Deepu — see root CLAUDE.md
"Development Ownership").

## Owned
- `scenarios.py` — `SCENARIOS`: the 5 minimum failure classes from
  `docs/EVALUATION.md` (`bad_deployment`, `db_slowdown`, `config_error`,
  `dependency_failure`, `resource_exhaustion`), each with the exact schema
  root CLAUDE.md section 19 requires (`scenario_id`, `description`,
  `fault_type`, `injection_method`, `expected_symptoms`,
  `ground_truth_root_cause`, `recovery_expectation`). `get_ground_truth()` is
  the ONE function meant to be called for scoring — it returns only
  `{scenario_id, ground_truth_root_cause, recovery_expectation}`, never the
  full scenario (which would leak `expected_symptoms` hints too).
- `injector.py` — bounded HTTP client to `production/service.py`'s
  `/admin/fault/*` endpoints only (`inject(scenario_id)`, `clear()`,
  `current_state()`). Separate module from `guardrails/production_client.py`
  and `mcp/production_client.py` (dependency isolation).

## Contract
Each scenario's `fault_type` maps 1:1 onto `production/state.py`'s
`FAULT_TYPES` — injecting a scenario genuinely degrades real request
behavior (real elevated error rate and/or latency through the existing
`/metrics`, `/logs`, `/db/diagnostics`, `/changes` endpoints), it does not
set a label agents can read directly. Diagnostic/evidence/critic/recovery
agents have no import path to this package at all.

## Rules
Never hard-code a scenario's `ground_truth_root_cause` into `agents/`,
`orchestrator/`, or `guardrails/` — ground truth lives here and in
`evaluation/` only, read by `evaluation/run_experiment.py` after the fact for
scoring, never fed into any agent prompt or MCP tool response.

## Dependency isolation
No dedicated venv needed — only dependency is `httpx`, already present in
every other venv. Runs fine from `.venv-orchestrator/` or a plain venv.

## Status
Phase 9: **implemented + tested**. `fault_injection/tests/test_scenarios.py`
(5 pure unit tests) and `test_injector_live.py` (2 real tests against a live
`production/` instance) both pass — see `docs/PROJECT_STATE.md` "Phase 9".

## Test
```bash
python -m pytest fault_injection/tests/test_scenarios.py -q     # pure, no network
# production/ must be running for the live test:
python -m pytest fault_injection/tests/test_injector_live.py -q
```

## Usually inspect
`scenarios.py`, `injector.py`, `production/state.py`, `docs/EVALUATION.md`

## Usually don't touch
`agents/`, `orchestrator/`, `guardrails/` (must never import this package)
