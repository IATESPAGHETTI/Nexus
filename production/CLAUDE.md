# Production (Simulated) Local Instructions

## Purpose
Simulated production-like service that NEXUS investigates. Deliberately labeled
"simulated" per root CLAUDE.md rule 4 — this is a controlled research environment,
not real production. Vanshika's workstream (implemented by Deepu).

## Owned
- `service.py` — FastAPI app + request-observing middleware. All HTTP endpoints live here.
- `observability.py` — in-process, thread-safe metrics/logs/traces/query stores (real
  data from real requests, not fabricated).
- `db.py` — seeded in-memory SQLite (`orders` table) with real query timing recorded
  into `observability.query_store`. Phase 9: sleeps `state.DB_SLOWDOWN_SECONDS`
  before every query while `state.db_slowdown` is set — a real, not fabricated,
  slower query.
- `changes.py` — simulated deployment/change history. `append()` (Phase 8/9) is
  called for real by `service.py`'s fault-injection and rollback-recovery
  admin endpoints — a "bad deployment" fault and its rollback both leave a
  real entry in the same timeline the Change Analysis Agent already queries.
- `state.py` (Phase 8/9) — the only mutable state in `production/`. Thread-safe
  flags for the 5 fault types (`bad_deployment`, `db_slowdown`, `config_error`,
  `dependency_failure`, `resource_exhaustion`) plus `deployed_version`. Only
  ever mutated through `service.py`'s `/admin/*` endpoints — never directly
  by an agent.

## Contract (see docs/API_CONTRACT.md for the authoritative version)
```text
GET  /health              liveness
GET  /metrics             request counts/latency by endpoint
GET  /logs?limit=N        recent structured request logs
GET  /traces?limit=N      recent request trace summaries
GET  /traces/{trace_id}   single trace detail (404 if unknown)
GET  /changes?limit=N     simulated deployment/change history, newest first
GET  /db/diagnostics      row counts + recent query timings from the seeded DB
GET  /orders              demo endpoint that runs a real SQLite query
GET  /orders/{id}         single order lookup (404 if unknown)

# Phase 8/9 admin endpoints -- mutating; only fault_injection/injector.py and
# guardrails/production_client.py are expected to call these:
GET  /admin/state                             real fault-state snapshot
POST /admin/fault/inject   {fault_type, bad_version?}
POST /admin/fault/clear
POST /admin/recovery/restart_service
POST /admin/recovery/rollback_deployment {target_version}
POST /admin/recovery/reset_config
POST /admin/recovery/scale_resources
```
Every request gets an `X-Trace-Id` response header and is recorded into metrics/logs/
traces automatically via the middleware in `service.py` — don't bypass it by adding
raw ASGI routes.

## Rules
Never let this service be mistaken for real production. Any fault injected here is
reversible (`state.py`'s flags, cleared by `/admin/fault/clear` or a matching
recovery action) and only reachable through `fault_injection/`'s
`/admin/fault/*` calls or `guardrails/`'s `/admin/recovery/*` calls — never a
diagnostic/evidence/critic/recovery agent directly. The DB is in-memory and
reseeds on every process restart — don't assume persistence across restarts.

## Local commands
```bash
uvicorn service:app --reload --port 8001
```

## Test
```bash
pytest tests/test_health.py tests/test_observability.py tests/test_fault_recovery.py
```
`test_fault_recovery.py` (Phase 8/9): 11 `TestClient` tests — every fault
type's real symptom (deterministic config_error failures, real db_slowdown
latency, bad_deployment's change-history entry), every recovery action's
real state mutation, and `/admin/fault/clear`.

## Usually inspect
`service.py`, `observability.py`, `db.py`, `changes.py`, `state.py`, `docs/API_CONTRACT.md`

## Status
Phase 2 (Observability) complete and verified. Phase 8/9 (fault-injectable +
recoverable mutable state) complete and verified — see `docs/PROJECT_STATE.md`.
