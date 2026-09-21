"""Bounded configuration for the NEXUS guardrails/recovery-execution layer.

No secrets live here (same rule as mcp/config.py). This module is the single
source of truth for which recovery actions exist at all -- an action name not
in `ALLOWED_ACTIONS` cannot be validated, approved, or executed no matter what
a RecoveryAgent proposes (root CLAUDE.md section 20: recovery must never be an
unrestricted autonomous action).
"""

from __future__ import annotations

import os
from pathlib import Path

PRODUCTION_BASE_URL = os.environ.get("PRODUCTION_BASE_URL", "http://localhost:8001")
HTTP_TIMEOUT_SECONDS = 5.0

REPO_ROOT = Path(__file__).resolve().parents[1]

# Every recovery action guardrails/executor.py is willing to actually perform,
# each bound to exactly one production/ admin endpoint. `required_params` is
# the exact, closed set of parameter names accepted for that action -- an
# extra/unexpected param is dropped, not silently forwarded.
ALLOWED_ACTIONS: dict[str, dict] = {
    "restart_service": {
        "endpoint": "/admin/recovery/restart_service",
        "required_params": (),
        "risk_level": "LOW",
        "blast_radius": "single-service, transient-state-only",
        "addresses_faults": ("resource_exhaustion", "dependency_failure"),
    },
    "rollback_deployment": {
        "endpoint": "/admin/recovery/rollback_deployment",
        "required_params": ("target_version",),
        "risk_level": "MEDIUM",
        "blast_radius": "single-service, reverts most recent deployment",
        "addresses_faults": ("bad_deployment",),
    },
    "reset_config": {
        "endpoint": "/admin/recovery/reset_config",
        "required_params": (),
        "risk_level": "LOW",
        "blast_radius": "single-service, configuration-only",
        "addresses_faults": ("config_error",),
    },
    "scale_resources": {
        "endpoint": "/admin/recovery/scale_resources",
        "required_params": (),
        "risk_level": "LOW",
        "blast_radius": "single-service, capacity-only",
        "addresses_faults": ("db_slowdown", "resource_exhaustion"),
    },
}

VALID_RISK_LEVELS = ("LOW", "MEDIUM", "HIGH")

# Bounds enforced by guardrails/policy.py -- never trust the agent-proposed
# plan's own size or the reasoning agent's own risk assessment unchecked.
MAX_ACTIONS_PER_PLAN = int(os.environ.get("MAX_ACTIONS_PER_PLAN", "3"))
MAX_RISK_LEVEL_ALLOWED = os.environ.get("MAX_RISK_LEVEL_ALLOWED", "MEDIUM")  # HIGH always rejected

# Kill switch: a sentinel file whose mere existence refuses all execution,
# re-checked live before every single action (not just once per plan) so it
# can be engaged mid-execution during a demo. Never an env var alone -- a
# file can be toggled without restarting the orchestrator process.
KILL_SWITCH_PATH = Path(os.environ.get("NEXUS_KILL_SWITCH_PATH", str(REPO_ROOT / "guardrails" / ".kill_switch")))

# How long orchestrator/recovery.py will poll backend/ waiting for a human's
# POST /incidents/{id}/approve before giving up (root CLAUDE.md section 20:
# recovery always requires human approval; it must also be boundable, never
# an indefinite hang). Default raised from 120s to 600s: a person reading the
# plan in the dashboard needs longer than two minutes, and once the window
# closes the orchestrator has exited, so a late "approve" cannot execute anything.
MAX_APPROVAL_WAIT_SECONDS = int(os.environ.get("MAX_APPROVAL_WAIT_SECONDS", "600"))
APPROVAL_POLL_INTERVAL_SECONDS = float(os.environ.get("APPROVAL_POLL_INTERVAL_SECONDS", "2"))
