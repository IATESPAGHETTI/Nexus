import random
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import changes
import db
import state
from observability import log_store, metrics_store, new_trace_id, now_iso, query_store, trace_store

app = FastAPI(title="nexus-production-simulated")

# Phase 9: real, bounded synthetic degradation applied to every request while
# state.resource_exhaustion is set -- an actual sleep and an actual chance of a
# real 500, not a fabricated metric.
RESOURCE_EXHAUSTION_LATENCY_SECONDS = 0.15
RESOURCE_EXHAUSTION_ERROR_RATE = 0.08


def _record_request(request: Request, trace_id: str, status_code: int, duration_ms: float) -> None:
    # /admin/* is the test/recovery control plane, not customer traffic. Recording it would
    # let diagnostic agents read "POST /admin/fault/inject" in the logs and traces, i.e. see
    # the test harness instead of diagnosing symptoms.
    if request.url.path.startswith("/admin"):
        return
    is_error = status_code >= 500
    endpoint = f"{request.method} {request.url.path}"
    metrics_store.record(endpoint, duration_ms, is_error)
    log_store.add(
        {
            "timestamp": now_iso(),
            "level": "ERROR" if is_error else "INFO",
            "trace_id": trace_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
        }
    )
    trace_store.add(
        {
            "trace_id": trace_id,
            "timestamp": now_iso(),
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": round(duration_ms, 2),
        }
    )


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    trace_id = new_trace_id()
    start = time.perf_counter()

    # /admin/* is the fault-injection/recovery control plane, not simulated
    # production traffic -- it must stay reliable even while
    # resource_exhaustion is set, otherwise the very recovery action meant to
    # clear the fault (POST /admin/recovery/scale_resources) could randomly
    # fail because of the fault it is fixing.
    if not request.url.path.startswith("/admin") and state.snapshot()["resource_exhaustion"]:
        time.sleep(RESOURCE_EXHAUSTION_LATENCY_SECONDS)
        if random.random() < RESOURCE_EXHAUSTION_ERROR_RATE:
            duration_ms = (time.perf_counter() - start) * 1000
            _record_request(request, trace_id, 500, duration_ms)
            response = JSONResponse(
                status_code=500,
                content={"detail": "ResourceExhaustedError: memory limit exceeded"},
            )
            response.headers["X-Trace-Id"] = trace_id
            return response

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        status_code = 500
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        _record_request(request, trace_id, status_code, duration_ms)
    response.headers["X-Trace-Id"] = trace_id
    return response


@app.get("/")
def root() -> dict:
    return {"status": "ok", "service": "nexus-production"}


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "nexus-production"}


@app.get("/metrics")
def metrics() -> dict:
    return metrics_store.snapshot()


@app.get("/logs")
def logs(limit: int = 50) -> dict:
    return {"entries": log_store.recent(limit=limit)}


@app.get("/traces")
def traces(limit: int = 20) -> dict:
    return {"traces": trace_store.recent(limit=limit)}


@app.get("/traces/{trace_id}")
def trace_detail(trace_id: str) -> dict:
    trace = trace_store.get(trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="trace not found")
    return trace


@app.get("/changes")
def change_history(limit: int = 20) -> dict:
    return {"changes": changes.recent(limit=limit)}


@app.get("/db/diagnostics")
def db_diagnostics() -> dict:
    return db.diagnostics()


def _check_order_endpoint_faults() -> None:
    """Real, deterministic-where-possible symptoms for the order endpoints,
    consulted by both /orders and /orders/{id} (Phase 9 fault injection).
    Raises the same HTTPException a genuinely broken service would raise."""
    snap = state.snapshot()
    if snap["config_error"]:
        # Deterministic (100%), not flaky -- distinguishes a configuration
        # error from the partial/random bad_deployment error rate below.
        raise HTTPException(status_code=500, detail="ConfigError: DB_POOL_SIZE must be > 0, got 0")
    if snap["bad_deployment"]:
        if random.random() < 0.35:
            raise HTTPException(
                status_code=500,
                detail="OrderServiceError: 'NoneType' object has no attribute 'total'",
            )


@app.get("/orders")
def list_orders() -> dict:
    _check_order_endpoint_faults()
    rows = db.run_query("SELECT * FROM orders ORDER BY id")
    return {"orders": [dict(row) for row in rows]}


@app.get("/orders/{order_id}")
def get_order(order_id: int) -> dict:
    _check_order_endpoint_faults()
    if state.snapshot()["dependency_failure"] and random.random() < 0.5:
        # Simulated downstream call: real added latency before the real
        # failure, not an instant fake error.
        time.sleep(1.5)
        raise HTTPException(status_code=500, detail="DependencyTimeoutError: payment-service unreachable")
    rows = db.run_query("SELECT * FROM orders WHERE id = ?", (order_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="order not found")
    return dict(rows[0])


# ---------------------------------------------------------------------------
# Admin endpoints (Phase 8/9) -- mutating, unlike every endpoint above.
#
# Only two real callers are expected to ever call these:
#   - fault_injection/injector.py  -> POST /admin/fault/inject, /admin/fault/clear
#   - guardrails/production_client.py -> POST /admin/recovery/*
# Diagnostic/evidence/critic/recovery agents never call these directly (see
# this module's docstring and production/CLAUDE.md).
# ---------------------------------------------------------------------------


class FaultInjectRequest(BaseModel):
    fault_type: str
    bad_version: str | None = None


class RollbackRequest(BaseModel):
    target_version: str


@app.get("/admin/state")
def admin_state() -> dict:
    return state.snapshot()


@app.post("/admin/fault/inject")
def admin_inject_fault(body: FaultInjectRequest) -> dict:
    try:
        new_state = state.inject(body.fault_type, bad_version=body.bad_version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if body.fault_type == "bad_deployment":
        changes.append(
            "deployment",
            new_state["deployed_version"],
            "Deploy: refactored order total calculation",
            author="ci-pipeline",
        )
    return new_state


@app.post("/admin/fault/clear")
def admin_clear_fault() -> dict:
    return state.clear_all()


@app.post("/admin/reset")
def admin_reset() -> dict:
    """Test/demo reset for repeatable benchmarks: clears faults AND all accumulated
    evidence (injected change records, metrics, logs, traces, query log) so one
    scenario's residue cannot leak into the next."""
    new_state = state.clear_all()
    changes.reset()
    metrics_store.clear()
    log_store.clear()
    trace_store.clear()
    query_store.clear()
    return new_state


@app.post("/admin/recovery/restart_service")
def admin_restart_service() -> dict:
    return state.restart_service()


@app.post("/admin/recovery/rollback_deployment")
def admin_rollback_deployment(body: RollbackRequest) -> dict:
    try:
        new_state = state.rollback_deployment(body.target_version)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    changes.append("deployment", body.target_version, "Rollback recovery action", author="guardrails")
    return new_state


@app.post("/admin/recovery/reset_config")
def admin_reset_config() -> dict:
    return state.reset_config()


@app.post("/admin/recovery/scale_resources")
def admin_scale_resources() -> dict:
    return state.scale_resources()
