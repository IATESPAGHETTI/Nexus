# Guardrails Local Instructions

## Purpose
Safety layer for recovery: safety validation, human approval gating, bounded
execution, kill switch. This is the ONLY code in the entire NEXUS system with
real execution capability — the Recovery Agent (`agents/recovery/`) is an LLM
with zero tools and can only ever emit a JSON proposal; guardrails is what
independently re-validates and actually calls a mutating endpoint.

## Owned
- `config.py` — no secrets. `ALLOWED_ACTIONS`: the single authoritative
  allowlist of every recovery action guardrails is willing to perform
  (`restart_service`, `rollback_deployment`, `reset_config`,
  `scale_resources`), each bound to exactly one `production/` admin endpoint,
  its required params, risk level, and blast radius. `MAX_ACTIONS_PER_PLAN`,
  `MAX_RISK_LEVEL_ALLOWED` (HIGH always rejected), `KILL_SWITCH_PATH`,
  `MAX_APPROVAL_WAIT_SECONDS`/`APPROVAL_POLL_INTERVAL_SECONDS`.
- `production_client.py` — bounded (5s timeout) HTTP client to `production/`'s
  mutating `/admin/recovery/*` endpoints only. Separate from
  `mcp/production_client.py` and `fault_injection/injector.py` (dependency
  isolation, same principle as every other top-level folder) even though the
  shape is similar.
- `audit.py` — local in-process audit log of every guardrails action (mirrors
  `mcp/audit.py`'s pattern exactly).
- `kill_switch.py` — file-based (not env-var-based) kill switch:
  `is_engaged()` is re-checked live before EVERY action in `executor.py`, so
  it can be flipped mid-execution. `python guardrails/kill_switch.py
  [engage|disengage|status]` (run from repo root).
- `policy.py` — `validate_plan(plan) -> SafetyValidationResult`. Pure,
  deterministic, no LLM. A second, independent gate on top of
  `agents/recovery/agent.py`'s own structural enforcement — re-validates
  every action/param/risk_level against `config.ALLOWED_ACTIONS` from
  scratch. ANY invalid action/param/risk/missing-rollback-plan rejects the
  WHOLE plan (never silently drops the bad part and approves the rest).
- `remedy.py` (2026-10-11) — deterministic "can this plan fix what the evidence
  shows" check used by `policy.validate_plan(plan, evidence_pool)` and to build
  the Recovery Agent's `remedy_guidance`. Reads only MCP evidence (never the
  simulator's ground truth); recognises db_slowdown / config_error /
  dependency_failure / resource_exhaustion; no recognised symptom = no opinion.
- `executor.py` — `execute_plan(plan) -> {"action_history", "all_succeeded",
  "kill_switch_engaged"}`. Runs each already-approved action in order via
  `production_client.py`; re-checks the kill switch before every single
  action; stops immediately (does not continue) on the kill switch or on any
  action's own failure — a partially-executed plan is recorded exactly as it
  happened, never retried automatically.

## Contract
Recovery flow (root CLAUDE.md section 20), implemented end-to-end in
`orchestrator/recovery.py`, which is the only caller of this package:

```text
Diagnosis -> Recovery Agent (real A2A, no execution capability)
   -> guardrails.policy.validate_plan()          [REJECTED stops here]
   -> approval_state=PENDING, human polls out-of-band via backend/'s
      POST /incidents/{id}/approve                [REJECTED/EXPIRED stops here]
   -> guardrails.executor.execute_plan()          [kill-switch-gated, bounded]
   -> verification (real second A2A call to metrics_agent)
   -> RESOLVED only on verified success
```
No step may be skipped — `orchestrator/recovery.py` calls these in exactly
this order and never bypasses `validate_plan`/the approval wait/the kill
switch check, even in a demo.

## Dependency isolation
No dedicated venv: the only third-party dependency is `httpx`, already
pinned identically in `orchestrator/requirements.txt` — `guardrails/`
imports run inside `.venv-orchestrator/` (see `orchestrator/recovery.py`'s
`sys.path.insert`). `guardrails/requirements.txt` documents this rather than
describing a separate install.

## Rules
No autonomous destructive production action, ever — human approval is
mandatory for every plan that passes safety validation, with no override,
including "the demo needs to finish." Never trust anything from
`agents/recovery/agent.py`'s raw model output directly — every action is
re-looked-up in `config.ALLOWED_ACTIONS` by name; a plan is never turned into
an HTTP request built from arbitrary text.

## Status
Phase 8: **implemented + tested** (guardrails/tests/test_policy_executor.py,
14 unit tests, no network; also verified live against a real running
`production/` instance — see `docs/PROJECT_STATE.md` "Phase 8" for the exact
real inject -> validate -> execute -> verify and kill-switch-mid-execution
runs performed).

## Test
```bash
python -m pytest guardrails/tests -q
```
14 fast, deterministic unit tests: `policy.validate_plan`'s every
rejection/approval path, `executor.execute_plan`'s ordering/kill-switch/
failure-stops-remaining-actions/param-dropping behavior (production_client.post
monkeypatched), and the kill switch's engage/disengage round trip.

## Usually inspect
`policy.py`, `executor.py`, `config.py`, `kill_switch.py`,
`orchestrator/recovery.py`, `agents/recovery/agent.py`, `docs/API_CONTRACT.md`

## Usually don't touch
`agents/`, `backend/`, `production/` (separate verified components) —
guardrails only ever reaches `production/` through `production_client.py`'s
fixed set of admin-endpoint calls.
