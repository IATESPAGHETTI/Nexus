"""Mutable, thread-safe simulated production state (Phase 8/9).

Everything in Phase 1/2 (`observability.py`, `db.py`, `changes.py`) was
read-only from the outside. Phase 8 (recovery) and Phase 9 (fault injection)
need something that can actually get worse and actually get better. This
module is that mutable state: `service.py`'s real request path consults it on
every request and genuinely behaves worse while a fault flag is set (added
latency, real 5xx responses) -- `observability.py` then records that
genuinely-degraded behavior the same way it records everything else. Nothing
here is faked; a flag flip here has a real, observable effect on the real
HTTP responses this service returns.

Only reachable through:
  - `fault_injection/` (injects faults, via `service.py`'s `/admin/fault/*`
    endpoints) -- root CLAUDE.md section 19 / `fault_injection/CLAUDE.md`.
  - `guardrails/` (executes recovery actions, via `service.py`'s
    `/admin/recovery/*` endpoints) -- root CLAUDE.md section 20 /
    `guardrails/CLAUDE.md`.
Diagnostic/evidence/critic/recovery agents never call these endpoints or this
module directly -- they only ever observe the *symptoms* this state produces
through the existing, unchanged Phase 2 read-only endpoints
(`/metrics`, `/logs`, `/traces`, `/db/diagnostics`, `/changes`).
"""

from __future__ import annotations

from dataclasses import dataclass
from threading import Lock

DEFAULT_VERSION = "1.1.0"

FAULT_TYPES = (
    "bad_deployment",
    "db_slowdown",
    "config_error",
    "dependency_failure",
    "resource_exhaustion",
)


@dataclass
class ServiceState:
    deployed_version: str = DEFAULT_VERSION
    bad_deployment: bool = False
    db_slowdown: bool = False
    config_error: bool = False
    dependency_failure: bool = False
    resource_exhaustion: bool = False

    def snapshot(self) -> dict:
        return {
            "deployed_version": self.deployed_version,
            "bad_deployment": self.bad_deployment,
            "db_slowdown": self.db_slowdown,
            "config_error": self.config_error,
            "dependency_failure": self.dependency_failure,
            "resource_exhaustion": self.resource_exhaustion,
        }


_lock = Lock()
_state = ServiceState()


def snapshot() -> dict:
    with _lock:
        return _state.snapshot()


def inject(fault_type: str, bad_version: str | None = None) -> dict:
    """Fault injection only -- never called by recovery/guardrails."""
    if fault_type not in FAULT_TYPES:
        raise ValueError(f"fault_type must be one of {FAULT_TYPES}")
    with _lock:
        if fault_type == "bad_deployment":
            _state.bad_deployment = True
            _state.deployed_version = bad_version or "1.2.0-bad"
        else:
            setattr(_state, fault_type, True)
        return _state.snapshot()


def clear_all() -> dict:
    """Fault injection cleanup only (test/demo reset) -- distinct from the
    individual, named recovery actions below, which guardrails/ uses."""
    global _state
    with _lock:
        _state = ServiceState()
        return _state.snapshot()


def restart_service() -> dict:
    """Recovery action: clears transient faults a process restart would
    plausibly fix (a stuck dependency, a resource spike) -- does NOT touch
    `bad_deployment` or `config_error`, which need a real corrective action."""
    with _lock:
        _state.resource_exhaustion = False
        _state.dependency_failure = False
        return _state.snapshot()


def rollback_deployment(target_version: str) -> dict:
    """Recovery action: reverts to a named prior version, clearing the
    bad_deployment fault."""
    if not target_version or not isinstance(target_version, str):
        raise ValueError("target_version must be a non-empty string")
    with _lock:
        _state.bad_deployment = False
        _state.deployed_version = target_version
        return _state.snapshot()


def reset_config() -> dict:
    """Recovery action: clears the config_error fault."""
    with _lock:
        _state.config_error = False
        return _state.snapshot()


def scale_resources() -> dict:
    """Recovery action: adds bounded service capacity, clearing the simulated
    capacity and database-load faults that it can actually remediate."""
    with _lock:
        _state.resource_exhaustion = False
        _state.db_slowdown = False
        return _state.snapshot()
