# Backend Local Instructions

## Purpose
NEXUS persistence + API layer: incident state, event store, HTTP API, human approval
endpoint. Owned by Vanshika's workstream (implemented by Deepu — see root CLAUDE.md).

## Owned
- `app/main.py` — FastAPI app. `GET /health` (Phase 1). Phase 6: `POST /incidents`,
  `GET /incidents/{id}`, `POST /incidents/{id}/state`, `POST /incidents/{id}/events`,
  `GET /incidents/{id}/events` — real incident state + event store, called for
  real by `orchestrator/event_bridge.py` during a live investigation (not just
  by tests). Human-approval endpoint still planned (Phase 8, recovery).
- `app/incident_store.py` (Phase 6) — thread-safe in-memory incident state +
  event store (same `Lock` + `dict` pattern as `production/observability.py`).
  Implements the incident-state field set from root CLAUDE.md section 15 and
  the event envelope from `docs/EVENT_SCHEMA.md`. In-memory only (resets on
  process restart) — see "Known limitations" in `docs/PROJECT_STATE.md`; no
  durable storage was required for Phase 6.

## Contract
See `docs/API_CONTRACT.md` for the HTTP API and `docs/EVENT_SCHEMA.md` for the event
shape this service must persist and re-emit to the dashboard.

## Rules
No business logic here beyond persistence/serving — reasoning belongs in `orchestrator/`
and `agents/`. Do not let this service call production systems directly.

## Local commands
```bash
uvicorn app.main:app --reload --port 8000
```

## Test
```bash
pytest tests/test_health.py tests/test_incidents.py
```
`test_incidents.py` (Phase 6): 6 `TestClient` tests, no network — incident
creation, 404s on unknown incident_id, event append + timeline/list, and
partial-state-merge semantics.

## Usually inspect
`app/main.py`, `app/incident_store.py`, `docs/API_CONTRACT.md`, `docs/EVENT_SCHEMA.md`

## Usually don't touch
`production/` (separate service, simulated target system)
