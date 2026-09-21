# Backend Local Instructions

## Purpose
NEXUS persistence + API layer: incident state, event store, HTTP API, human approval
endpoint. Owned by Vanshika's workstream (implemented by Deepu — see root CLAUDE.md).

## Owned
- `app/main.py` — FastAPI app. `GET /health` (Phase 1). Phase 6: `POST /incidents`,
  `GET /incidents/{id}`, `POST /incidents/{id}/state`, `POST /incidents/{id}/events`,
  `GET /incidents/{id}/events` — real incident state + event store, called for
  real by `orchestrator/event_bridge.py` during a live investigation (not just
  by tests). Phase 8: `POST /incidents/{id}/approve` — the human approval gate
  `orchestrator/recovery.py` polls for; persistence only (records a real
  human decision made outside this process, appends
  `HUMAN_APPROVAL_GRANTED`/`HUMAN_APPROVAL_REJECTED`), never decides anything
  itself.
- `app/incident_store.py` (Phase 6) — thread-safe in-memory incident state +
  event store (same `Lock` + `dict` pattern as `production/observability.py`).
  Implements the incident-state field set from root CLAUDE.md section 15 and
  the event envelope from `docs/EVENT_SCHEMA.md`. In-memory only (resets on
  process restart) — see "Known limitations" in `docs/PROJECT_STATE.md`; no
  durable storage was required for Phase 6.
- `app/demo.py` (Phase 10, "Inject Controlled Failure") — the ONE deliberate,
  narrow exception to the "no business logic" rule below. `GET /demo/status`:
  real HTTP probes (production `/health`, each of the 7 A2A agents'
  `.well-known/agent-card.json`) — never a hardcoded "online". `POST
  /demo/investigate`: calls production's real `/admin/fault/inject` (the
  same mechanism `fault_injection/injector.py` uses), creates a real
  incident via `incident_store`, and — only if at least one agent service is
  reachable — launches the real `orchestrator/investigation.py`
  `run_investigation()` as a detached `.venv-orchestrator/` subprocess
  (`orchestrator/run_demo.py --incident-id <id>`), since backend/'s own venv
  deliberately excludes google-adk/litellm/a2a-sdk (root CLAUDE.md section
  23). Invents no fault types, no investigation logic, no recovery logic —
  it only bridges a dashboard button click to code that already exists
  elsewhere.

## Contract
See `docs/API_CONTRACT.md` for the HTTP API and `docs/EVENT_SCHEMA.md` for the event
shape this service must persist and re-emit to the dashboard.

## Rules
No business logic here beyond persistence/serving and the one Phase 10
exception above (`app/demo.py`) — reasoning belongs in `orchestrator/` and
`agents/`. Do not let this service call production systems directly except
through `app/demo.py`'s narrow, real, already-existing endpoints.

## Local commands
```bash
uvicorn app.main:app --reload --port 8000
```

## Test
```bash
pytest tests/test_health.py tests/test_incidents.py
```
`test_incidents.py`: 10 `TestClient` tests, no network — incident creation,
404s on unknown incident_id, event append + timeline/list, partial-state-merge
semantics (Phase 6), and the approve endpoint's decision recording +
`HUMAN_APPROVAL_GRANTED`/`REJECTED` event emission + 400 on an invalid
decision value + 404 on an unknown incident (Phase 8).

## Usually inspect
`app/main.py`, `app/incident_store.py`, `docs/API_CONTRACT.md`, `docs/EVENT_SCHEMA.md`

## Usually don't touch
`production/` (separate service, simulated target system)
