import time

from fastapi import FastAPI, HTTPException, Request

import changes
import db
from observability import log_store, metrics_store, new_trace_id, now_iso, trace_store

app = FastAPI(title="nexus-production-simulated")


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    trace_id = new_trace_id()
    start = time.perf_counter()
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        status_code = 500
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
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


@app.get("/orders")
def list_orders() -> dict:
    rows = db.run_query("SELECT * FROM orders ORDER BY id")
    return {"orders": [dict(row) for row in rows]}


@app.get("/orders/{order_id}")
def get_order(order_id: int) -> dict:
    rows = db.run_query("SELECT * FROM orders WHERE id = ?", (order_id,))
    if not rows:
        raise HTTPException(status_code=404, detail="order not found")
    return dict(rows[0])
