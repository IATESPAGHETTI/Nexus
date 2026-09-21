"""Bounded execution of an already-validated, already-human-approved recovery
plan (root CLAUDE.md section 20: ... -> Sandbox/controlled execution ->
Verification -> Resolved/failed/escalated).

This module is the ONLY code in the entire system that actually calls a
mutating production/ endpoint. The RecoveryAgent (LLM) never gets tool access
(agents/recovery/agent.py is a ReasoningAgent with tools=[]) -- it can only
ever *propose* a plan as JSON text. Nothing that text says is trusted here:
every action is re-looked-up in `config.ALLOWED_ACTIONS` (never a string built
from the plan), and the kill switch is re-checked live before each one, so an
already-approved plan can still be stopped mid-execution.
"""

from __future__ import annotations

import time

import audit
import kill_switch
import production_client
from config import ALLOWED_ACTIONS


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _run_one_action(action_name: str, params: dict) -> dict:
    spec = ALLOWED_ACTIONS[action_name]
    body = {k: params[k] for k in spec["required_params"]}
    result = production_client.post(spec["endpoint"], json=body)
    return result


def execute_plan(plan: dict) -> dict:
    """Executes `plan["actions"]` in order. Stops immediately (does not run
    remaining actions) the moment the kill switch is found engaged, or an
    action's own call fails -- a partially-executed plan is recorded exactly
    as it happened, never retried automatically and never reported as fully
    succeeded.

    Returns:
    {
      "plan_id": ...,
      "action_history": [
        {"action", "params", "status": "EXECUTED"|"FAILED"|"SKIPPED_KILL_SWITCH",
         "detail", "timestamp"},
        ...
      ],
      "all_succeeded": bool,
      "kill_switch_engaged": bool,
    }
    """
    action_history: list[dict] = []
    all_succeeded = True
    switch_tripped = False

    for item in plan.get("actions", []):
        name = item.get("action")
        params = item.get("params") or {}

        if kill_switch.is_engaged():
            switch_tripped = True
            entry = {
                "action": name,
                "params": params,
                "status": "SKIPPED_KILL_SWITCH",
                "detail": "kill switch engaged; execution halted before this action",
                "timestamp": _now_iso(),
            }
            action_history.append(entry)
            audit.record(name, params, ok=False, detail="kill switch engaged")
            all_succeeded = False
            break

        if name not in ALLOWED_ACTIONS:
            # Cannot happen for a plan that passed guardrails/policy.validate_plan,
            # but this module never trusts that upstream check alone.
            entry = {
                "action": name,
                "params": params,
                "status": "FAILED",
                "detail": f"'{name}' is not in ALLOWED_ACTIONS -- refused",
                "timestamp": _now_iso(),
            }
            action_history.append(entry)
            audit.record(str(name), params, ok=False, detail="not in ALLOWED_ACTIONS")
            all_succeeded = False
            break

        try:
            result = _run_one_action(name, params)
            entry = {
                "action": name,
                "params": params,
                "status": "EXECUTED",
                "detail": result,
                "timestamp": _now_iso(),
            }
            audit.record(name, params, ok=True, detail=str(result))
        except production_client.ProductionUnavailableError as exc:
            entry = {
                "action": name,
                "params": params,
                "status": "FAILED",
                "detail": str(exc),
                "timestamp": _now_iso(),
            }
            audit.record(name, params, ok=False, detail=str(exc))
            all_succeeded = False
            action_history.append(entry)
            break

        action_history.append(entry)

    return {
        "plan_id": plan.get("plan_id"),
        "action_history": action_history,
        "all_succeeded": all_succeeded,
        "kill_switch_engaged": switch_tripped,
    }
