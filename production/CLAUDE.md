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
  into `observability.query_store`.
- `changes.py` — static simulated deployment/change history list. `fault_injection/`
  will append entries here later to make a "bad deployment" scenario reachable.

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
```
Every request gets an `X-Trace-Id` response header and is recorded into metrics/logs/
traces automatically via the middleware in `service.py` — don't bypass it by adding
raw ASGI routes.

## Rules
Never let this service be mistaken for real production. Any fault injected here must
be reversible and only reachable through `fault_injection/`. The DB is in-memory and
reseeds on every process restart — don't assume persistence across restarts.

## Local commands
```bash
uvicorn service:app --reload --port 8001
```

## Test
```bash
pytest tests/test_health.py tests/test_observability.py
```

## Usually inspect
`service.py`, `observability.py`, `db.py`, `changes.py`, `docs/API_CONTRACT.md`

## Status
Phase 2 (Observability) complete and verified — see `docs/PROJECT_STATE.md`.
