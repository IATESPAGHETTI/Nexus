"""Safety validation (root CLAUDE.md section 20: Diagnosis -> Recovery Agent
-> Bounded recovery plan -> **Safety validation** -> Human approval -> ...).

Pure, deterministic Python -- no LLM call, no network. This is a second,
independent gate on top of `agents/recovery/agent.py`'s own structural
enforcement (`build_recovery_plan`, which already drops any action not in its
own local action catalog): even if that layer were ever weakened, a plan
still cannot reach execution without independently re-validating here against
`guardrails/config.py`'s `ALLOWED_ACTIONS` -- the one authoritative allowlist
for what guardrails/executor.py is willing to actually run.
"""

from __future__ import annotations

import time
import uuid

from config import ALLOWED_ACTIONS, MAX_ACTIONS_PER_PLAN, MAX_RISK_LEVEL_ALLOWED, VALID_RISK_LEVELS

_RISK_ORDER = {level: i for i, level in enumerate(VALID_RISK_LEVELS)}


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def validate_plan(plan: dict) -> dict:
    """Returns a SafetyValidationResult:

    {
      "validation_id": "SV-<hex8>",
      "plan_id": ...,
      "verdict": "APPROVED_FOR_HUMAN_REVIEW" | "REJECTED",
      "reasons": [str, ...],           # always non-empty on REJECTED
      "checked_actions": [str, ...],   # action names actually validated
      "timestamp": "...",
    }

    Never mutates `plan`. A plan that fails ANY check is REJECTED outright --
    guardrails does not silently drop bad actions and approve the rest; a
    partially-invalid plan is a plan the Recovery Agent got wrong and must not
    proceed to human approval at all.
    """
    reasons: list[str] = []
    checked: list[str] = []

    if not isinstance(plan, dict):
        return _result(None, "REJECTED", ["plan is not a JSON object"], checked)

    plan_id = plan.get("plan_id")
    actions = plan.get("actions")
    if not isinstance(actions, list) or not actions:
        reasons.append("plan has no actions")
        actions = []

    if len(actions) > MAX_ACTIONS_PER_PLAN:
        reasons.append(f"plan has {len(actions)} actions, exceeding MAX_ACTIONS_PER_PLAN={MAX_ACTIONS_PER_PLAN}")

    for item in actions:
        if not isinstance(item, dict):
            reasons.append(f"malformed action entry: {item!r}")
            continue
        name = item.get("action")
        checked.append(str(name))
        spec = ALLOWED_ACTIONS.get(name)
        if spec is None:
            reasons.append(f"action '{name}' is not in guardrails.config.ALLOWED_ACTIONS")
            continue
        params = item.get("params") or {}
        if not isinstance(params, dict):
            reasons.append(f"action '{name}' params must be an object")
            continue
        missing = [p for p in spec["required_params"] if p not in params]
        if missing:
            reasons.append(f"action '{name}' missing required params: {missing}")
        extra = [p for p in params if p not in spec["required_params"]]
        if extra:
            reasons.append(f"action '{name}' has unexpected params (dropped): {extra}")

    risk_level = plan.get("risk_level")
    if risk_level not in VALID_RISK_LEVELS:
        reasons.append(f"risk_level '{risk_level}' is not one of {VALID_RISK_LEVELS}")
    elif _RISK_ORDER[risk_level] > _RISK_ORDER[MAX_RISK_LEVEL_ALLOWED]:
        reasons.append(f"risk_level '{risk_level}' exceeds MAX_RISK_LEVEL_ALLOWED='{MAX_RISK_LEVEL_ALLOWED}'")

    if not plan.get("rollback_plan"):
        reasons.append("plan has no rollback_plan described")

    verdict = "REJECTED" if reasons else "APPROVED_FOR_HUMAN_REVIEW"
    return _result(plan_id, verdict, reasons, checked)


def _result(plan_id, verdict: str, reasons: list[str], checked: list[str]) -> dict:
    return {
        "validation_id": f"SV-{uuid.uuid4().hex[:8]}",
        "plan_id": plan_id,
        "verdict": verdict,
        "reasons": reasons,
        "checked_actions": checked,
        "timestamp": _now_iso(),
    }
