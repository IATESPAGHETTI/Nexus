"""The 7 NEXUS MCP diagnostic tools.

Each tool:
  - has an explicit, validated input schema (plain Python type hints -> the MCP SDK
    derives the JSON schema from these when the tool is registered in server.py)
  - returns a structured, bounded dict (never an unbounded blob)
  - never raises to the caller: internal errors become {"ok": False, "error": "..."}
  - is recorded in mcp.audit for local auditability (Phase 6 will bridge this into
    the real NEXUS event stream; see mcp/audit.py)
  - only reaches evidence through production_client (bounded HTTP calls to the
    Phase 2 simulated production service) or git_diff_tool (bounded, allowlisted
    git history of this repo) — no open-ended filesystem/shell/SQL access.
"""

from __future__ import annotations

import time
from functools import wraps
from typing import Any

import audit
import git_diff_tool
import production_client
from config import DIAGNOSTIC_NAMES


def _audited(name):
    def decorator(fn):
        @wraps(fn)
        def wrapper(**kwargs):
            start = time.perf_counter()
            try:
                result = fn(**kwargs)
                duration_ms = (time.perf_counter() - start) * 1000
                audit.record(name, kwargs, duration_ms, ok=True)
                return {"ok": True, **result}
            except (
                production_client.ProductionUnavailableError,
                production_client.ProductionNotFoundError,
                git_diff_tool.InvalidGitDiffPathError,
                git_diff_tool.GitDiffDisabledError,
                ValueError,
            ) as exc:
                duration_ms = (time.perf_counter() - start) * 1000
                audit.record(name, kwargs, duration_ms, ok=False, error=str(exc))
                return {"ok": False, "error": str(exc)}

        return wrapper

    return decorator


def _bounded_limit(limit: int, minimum: int = 1, maximum: int = 200) -> int:
    if not isinstance(limit, int):
        raise ValueError("limit must be an integer")
    return max(minimum, min(limit, maximum))


@_audited("get_metrics")
def get_metrics() -> dict[str, Any]:
    """Request counts, error counts, and latency (avg/p99) per endpoint from the
    simulated production service. No arguments."""
    return production_client.get("/metrics")


@_audited("query_logs")
def query_logs(level: str | None = None, limit: int = 50) -> dict[str, Any]:
    """Recent structured request logs from the simulated production service.

    level: optional filter, "INFO" or "ERROR". limit: max entries, 1-200.
    """
    if level is not None and level not in ("INFO", "ERROR"):
        raise ValueError("level must be 'INFO', 'ERROR', or omitted")
    bounded = _bounded_limit(limit)
    body = production_client.get("/logs", params={"limit": bounded})
    entries = body.get("entries", [])
    if level is not None:
        entries = [e for e in entries if e.get("level") == level]
    return {"entries": entries, "count": len(entries)}


@_audited("get_trace")
def get_trace(trace_id: str | None = None, limit: int = 20) -> dict[str, Any]:
    """A single trace by ID, or the most recent traces if no ID is given.

    trace_id: optional specific trace to fetch (404 -> ok:False). limit: 1-100,
    only used when trace_id is omitted.
    """
    if trace_id:
        trace = production_client.get(f"/traces/{trace_id}")
        return {"trace": trace}
    bounded = _bounded_limit(limit, maximum=100)
    body = production_client.get("/traces", params={"limit": bounded})
    return {"traces": body.get("traces", [])}


@_audited("get_recent_deployments")
def get_recent_deployments(limit: int = 20) -> dict[str, Any]:
    """Simulated deployment/change history, newest first.

    limit: max entries, 1-50.
    """
    bounded = _bounded_limit(limit, maximum=50)
    body = production_client.get("/changes", params={"limit": bounded})
    return {"changes": body.get("changes", [])}


@_audited("get_git_diff")
def get_git_diff(paths: list[str] | None = None, max_commits: int = 5) -> dict[str, Any]:
    """Real git history for this repo's deployable components (production/, backend/,
    mcp/, docs/ only — see config.GIT_DIFF_ALLOWED_PATHS). Evidence for "what changed
    in a bad deployment" style investigations.

    paths: subset of the allowed top-level paths, or omitted for all of them.
    max_commits: how many recent commits to include in the diff, capped at 5.
    """
    return git_diff_tool.get_diff(paths=paths, max_commits=max_commits)


@_audited("get_database_stats")
def get_database_stats() -> dict[str, Any]:
    """Row counts, status breakdown, and recent query timings from the simulated
    production database. No arguments."""
    return production_client.get("/db/diagnostics")


@_audited("run_diagnostic")
def run_diagnostic(name: str) -> dict[str, Any]:
    """Run one pre-approved, named diagnostic (never arbitrary code/SQL/shell).

    name: one of "connectivity_check", "error_rate_check", "order_status_check".
    """
    if name not in DIAGNOSTIC_NAMES:
        raise ValueError(f"name must be one of {DIAGNOSTIC_NAMES}")

    if name == "connectivity_check":
        try:
            health = production_client.get("/health")
            return {"diagnostic": name, "reachable": True, "detail": health}
        except production_client.ProductionUnavailableError as exc:
            return {"diagnostic": name, "reachable": False, "detail": str(exc)}

    if name == "error_rate_check":
        metrics = production_client.get("/metrics")
        total = metrics.get("request_count", 0)
        errors = metrics.get("error_count", 0)
        rate = (errors / total) if total else 0.0
        return {
            "diagnostic": name,
            "request_count": total,
            "error_count": errors,
            "error_rate": round(rate, 4),
        }

    diagnostics = production_client.get("/db/diagnostics")
    return {
        "diagnostic": name,
        "table_row_counts": diagnostics.get("table_row_counts", {}),
        "orders_by_status": diagnostics.get("orders_by_status", {}),
    }
