"""Incident Manager triage: which diagnostic agents are worth calling?

A real on-call lead does not page every specialist for every alert. This reads
ONLY the reported symptom text (and, on a later round, what the Root-Cause
Critic asked for). It never reads the injected fault or any ground truth, so it
stays blind-evaluation safe (root CLAUDE.md section 19).

Rules are plain keyword matches, deliberately simple and inspectable, not a
model call:
  - the Metrics Agent is always consulted first (a cheap broad look),
  - every other agent is consulted only if the text mentions its area,
  - at least two agents are always consulted, so one wrong keyword cannot
    leave the investigation with a single viewpoint,
  - on later rounds only the agents the Critic's request points at are asked
    again, and an agent skipped earlier is called as soon as it becomes relevant.
"""

from __future__ import annotations

import re

AREAS: dict[str, tuple[str, str]] = {
    # agent: (regex over lower-cased text, plain-English area)
    "metrics_agent": (r"slow|latenc|respon|timeout|time out|error|fail|5\d\d|spike|traffic|load|memory|cpu|resource|throughput|rate|degrad|metric", "request speed and error numbers"),
    "logs_traces_agent": (r"error|fail|exception|crash|timeout|time out|refus|unavailable|intermittent|5\d\d|trace|log|slow|latenc|stuck|hang", "what individual requests did"),
    "change_analysis_agent": (r"deploy|release|rollout|roll out|update|upgrade|version|config|setting|change|suddenly|started|began|since|after|recent|history|commit", "recent deployments and configuration changes"),
    "database_agent": (r"slow|latenc|query|queries|database|\bdb\b|sql|table|connection|pool|lock|index|storage|disk", "database health"),
}

ALWAYS = "metrics_agent"
MIN_AGENTS = 2


def select_agents(text: str, available: list[str], first_round: bool = True) -> tuple[list[str], list[dict]]:
    """Return (selected agents in a stable order, skipped [{agent, reason}]).

    first_round=False (a re-investigation): only agents the text points at are
    asked again; if it points at none, everyone is asked rather than no one."""
    lowered = (text or "").lower()
    selected: list[str] = []
    hits: dict[str, str] = {}
    for name in available:
        pattern, _ = AREAS.get(name, ("", ""))
        found = re.search(pattern, lowered) if pattern else None
        if found:
            hits[name] = found.group(0)
        if (first_round and name == ALWAYS) or found:
            selected.append(name)

    if not first_round and not selected:
        selected = list(available)
        for name in selected:
            hits[name] = "(the request did not name an area, so everyone looks again)"

    # Never rely on a single viewpoint on the first look.
    for name in available:
        if not first_round or len(selected) >= MIN_AGENTS:
            break
        if name not in selected:
            selected.append(name)
            hits[name] = "(added so at least two agents look)"

    selected = [n for n in available if n in selected]
    skipped = [
        {
            "agent": n,
            "reason": f"nothing in the report points at {AREAS.get(n, ('', 'its area'))[1]}",
        }
        for n in available
        if n not in selected
    ]
    return selected, skipped


def describe(selected: list[str], skipped: list[dict], round_no: int) -> dict:
    return {"round": round_no, "selected": selected, "skipped": skipped}
