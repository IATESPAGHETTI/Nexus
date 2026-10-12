"""Deterministic "does this fix match what the evidence shows" check.

Pure Python, no LLM, no network, and NO access to the simulator's ground truth
(never reads production/'s `/admin/state` -- that would turn the guardrail into
an oracle and invalidate the evaluation). It only looks at the same real MCP
tool results the diagnostic agents already gathered, and only recognises a
symptom when the evidence itself says so:

  - db_slowdown          : a database `avg_query_ms` at or above SLOW_QUERY_MS, OR the median of
                           the `recent_queries` durations at or above it (the average alone can be
                           diluted by many earlier fast queries)
  - config_error         : the text "ConfigError" in a tool result
  - dependency_failure   : the text "DependencyTimeoutError" in a tool result
  - resource_exhaustion  : the text "ResourceExhaustedError" in a tool result

`guardrails/config.py` ALLOWED_ACTIONS[...]["addresses_faults"] says which
action fixes which class. A plan is only rejected when a symptom IS recognised
and NONE of the plan's actions addresses any recognised symptom; no recognised
symptom (e.g. a bad deployment, which has no marker here) means no opinion.
"""

from __future__ import annotations

import json
import os

from config import ALLOWED_ACTIONS

SLOW_QUERY_MS = float(os.environ.get("GUARDRAIL_SLOW_QUERY_MS", "100"))

_TEXT_MARKERS = {
    "ConfigError": "config_error",
    "DependencyTimeoutError": "dependency_failure",
    "ResourceExhaustedError": "resource_exhaustion",
}


def _numbers_for_key(obj, key: str):
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, (int, float)) and not isinstance(v, bool):
                yield float(v)
            else:
                yield from _numbers_for_key(v, key)
    elif isinstance(obj, list):
        for item in obj:
            yield from _numbers_for_key(item, key)


def _recent_query_median_ms(result: dict) -> float | None:
    durations = [
        q["duration_ms"]
        for q in result.get("recent_queries", []) or []
        if isinstance(q, dict) and isinstance(q.get("duration_ms"), (int, float)) and not isinstance(q["duration_ms"], bool)
    ]
    if len(durations) < 3:
        return None
    ordered = sorted(durations)
    return float(ordered[len(ordered) // 2])


def detect_symptoms(evidence_pool: list[dict] | None) -> dict[str, str]:
    """Recognised symptom class -> the evidence_id that shows it."""
    found: dict[str, str] = {}
    for item in evidence_pool or []:
        if not isinstance(item, dict) or not isinstance(item.get("result"), dict):
            continue
        evidence_id = str(item.get("evidence_id"))
        result = item["result"]
        text = json.dumps(result, default=str)
        for marker, symptom in _TEXT_MARKERS.items():
            if marker in text:
                found.setdefault(symptom, evidence_id)
        recent_median = _recent_query_median_ms(result)
        if any(avg >= SLOW_QUERY_MS for avg in _numbers_for_key(result, "avg_query_ms")) or (
            recent_median is not None and recent_median >= SLOW_QUERY_MS
        ):
            found.setdefault("db_slowdown", evidence_id)
    return found


def actions_addressing(symptoms) -> list[str]:
    wanted = set(symptoms)
    return [name for name, spec in ALLOWED_ACTIONS.items() if wanted & set(spec["addresses_faults"])]


def guidance(evidence_pool: list[dict] | None) -> list[dict]:
    """Handed to the Recovery Agent up front so it picks a fitting action."""
    return [
        {"symptom": symptom, "evidence_id": evidence_id, "actions_that_address_it": actions_addressing([symptom])}
        for symptom, evidence_id in detect_symptoms(evidence_pool).items()
    ]


def mismatch_reason(plan_action_names: list[str], evidence_pool: list[dict] | None) -> str | None:
    """A rejection reason if symptoms are recognised but the plan fixes none of them."""
    symptoms = detect_symptoms(evidence_pool)
    if not symptoms:
        return None
    fixed = set()
    for name in plan_action_names:
        spec = ALLOWED_ACTIONS.get(name)
        if spec:
            fixed |= set(spec["addresses_faults"])
    if fixed & set(symptoms):
        return None
    shown = ", ".join(f"{s} (evidence {e})" for s, e in symptoms.items())
    return (
        f"plan does not address the symptom(s) the evidence shows: {shown}; "
        f"its action(s) {plan_action_names} address {sorted(fixed) or 'nothing recognised'}; "
        f"action(s) that do: {actions_addressing(symptoms)}"
    )
