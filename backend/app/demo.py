"""Phase 10: the "Inject Controlled Failure" live-demo trigger.

This is the ONE piece of business logic backend/ is allowed to own (see
backend/CLAUDE.md "no business logic here" -- the exception is this module,
which exists purely to bridge a dashboard button click to the real,
already-implemented fault-injection and orchestration code; it invents no
new fault types, no new investigation logic, and no new recovery logic).

Real, not simulated:
- Fault injection is a real HTTP call to production/'s own
  `/admin/fault/inject` (fault_injection/injector.py's exact mechanism,
  reused here rather than reimplemented).
- The investigation is the real `orchestrator/investigation.py`
  `run_investigation()` coroutine, launched via `orchestrator/run_demo.py`
  as a detached subprocess in its own venv (`.venv-orchestrator/`) --
  backend/'s own venv deliberately does not have google-adk/litellm/a2a-sdk
  installed (root CLAUDE.md section 23, dependency isolation), so this is
  the smallest safe way to trigger the real orchestrator without collapsing
  that isolation.
- Agent/A2A reachability is a real HTTP check against each service's real
  `.well-known/agent-card.json` -- never a hardcoded "online".

If no A2A agent services are reachable (the common case unless an operator
started them per docs/DEMO_RUNBOOK.md), the fault is still injected for real
and the incident still created for real, but the orchestrator subprocess is
not spawned -- there would be nothing real for it to talk to, and spawning
it anyway would just produce a fast, uninformative connection-error failure.
The response says so explicitly rather than pretending an investigation
started.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import httpx

PRODUCTION_URL = os.environ.get("NEXUS_PRODUCTION_URL", "http://127.0.0.1:8001")
_TIMEOUT = 3.0

# Mirrors agents/common/ports.py's A2A_PORTS -- duplicated rather than
# imported so backend/'s venv never needs agents/'s dependencies.
AGENT_PORTS: dict[str, int] = {
    "metrics_agent": 8101,
    "logs_traces_agent": 8102,
    "change_analysis_agent": 8103,
    "database_agent": 8104,
    "evidence_agent": 8105,
    "root_cause_critic": 8106,
    "recovery_agent": 8107,
}

# The 5 real fault types production/state.py's FAULT_TYPES actually supports
# (mirrors fault_injection/scenarios.py's ground-truth catalog).
FAULT_TYPES = {
    "bad_deployment",
    "db_slowdown",
    "config_error",
    "dependency_failure",
    "resource_exhaustion",
}

REPO_ROOT = Path(__file__).resolve().parents[2]
ORCHESTRATOR_PYTHON = REPO_ROOT / ".venv-orchestrator" / "Scripts" / "python.exe"
RUN_DEMO_SCRIPT = REPO_ROOT / "orchestrator" / "run_demo.py"
DEMO_LOG_DIR = REPO_ROOT / "backend" / ".demo_logs"


def check_production() -> bool:
    try:
        r = httpx.get(f"{PRODUCTION_URL}/health", timeout=_TIMEOUT)
        return r.status_code == 200
    except httpx.RequestError:
        return False


def check_agents() -> dict[str, bool]:
    reachable: dict[str, bool] = {}
    for name, port in AGENT_PORTS.items():
        try:
            r = httpx.get(f"http://127.0.0.1:{port}/.well-known/agent-card.json", timeout=_TIMEOUT)
            reachable[name] = r.status_code == 200
        except httpx.RequestError:
            reachable[name] = False
    return reachable


def system_status() -> dict:
    agents = check_agents()
    return {
        "production_reachable": check_production(),
        "agents": agents,
        "agents_reachable_count": sum(agents.values()),
        "agents_total": len(agents),
    }


class ProductionUnavailableError(Exception):
    pass


def inject_fault(fault_type: str) -> dict:
    if fault_type not in FAULT_TYPES:
        raise ValueError(f"unknown fault_type: {fault_type!r} (expected one of {sorted(FAULT_TYPES)})")
    try:
        r = httpx.post(
            f"{PRODUCTION_URL}/admin/fault/inject", json={"fault_type": fault_type}, timeout=_TIMEOUT
        )
    except httpx.RequestError as exc:
        raise ProductionUnavailableError(f"could not reach production/: {exc}") from exc
    if r.status_code >= 400:
        raise ProductionUnavailableError(f"production/ rejected fault injection: HTTP {r.status_code} {r.text}")
    return r.json()


def spawn_investigation(incident_id: str, description: str) -> bool:
    """Launches the real orchestrator subprocess against an already-created
    incident. Fire-and-forget: does not block on or wait for the real Groq/
    A2A calls it will make. Returns False (does not spawn) if the
    orchestrator venv/script isn't present, so a broken dev setup fails
    loudly in the response rather than as a silent background crash."""
    if not ORCHESTRATOR_PYTHON.exists() or not RUN_DEMO_SCRIPT.exists():
        return False
    DEMO_LOG_DIR.mkdir(exist_ok=True)
    log_path = DEMO_LOG_DIR / f"{incident_id}.log"
    with open(log_path, "w", encoding="utf-8") as log_file:
        subprocess.Popen(
            [str(ORCHESTRATOR_PYTHON), str(RUN_DEMO_SCRIPT), "--incident-id", incident_id, description],
            cwd=str(REPO_ROOT),
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
        )
    return True
