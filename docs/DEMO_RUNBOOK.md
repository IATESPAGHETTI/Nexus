# NEXUS End-to-End Demo Runbook

This is the reproducible procedure for the Phase 11/29 demo flow described in
root `CLAUDE.md` section 29. Every command below was actually run in the
Phase 10B session on 2026-09-18 **except** the one marked "REQUIRES LIVE
GROQ CALL" — that step was intentionally not run this session per explicit
instruction not to spend Groq/Gemini quota. Everything else (starting the
full 9-process stack, fault injection, real backend incident creation, and
clean teardown) is live-verified, not assumed.

## 0. Prerequisites
- Repo root `.env` with a real `GROQ_API_KEY` (only needed for step 4).
- The 4 isolated venvs already built: `.venv`, `.venv-agents`, `.venv-mcp`,
  `.venv-orchestrator` (see each component's local `CLAUDE.md` for the
  `pip install -r requirements.txt` command if any is missing).
- Nothing already listening on ports 8000, 8001, 8101-8107.

## 1. Start the production simulation + backend
```bash
cd production && ../.venv/Scripts/python -m uvicorn service:app --port 8001 &
cd backend    && ../.venv/Scripts/python -m uvicorn app.main:app --port 8000 &
```
Verify:
```bash
curl http://localhost:8001/health
curl http://localhost:8000/health
```

## 2. Start all 7 A2A agent services
Each is its own OS process on its own port (`agents/common/ports.py`).
```bash
.venv-agents/Scripts/python agents/metrics/a2a_service.py &
.venv-agents/Scripts/python agents/logs_traces/a2a_service.py &
.venv-agents/Scripts/python agents/change_analysis/a2a_service.py &
.venv-agents/Scripts/python agents/database/a2a_service.py &
.venv-agents/Scripts/python agents/evidence/a2a_service.py &
.venv-agents/Scripts/python agents/critic/a2a_service.py &
.venv-agents/Scripts/python agents/recovery/a2a_service.py &
```
Give them ~5-8s to finish ADK/A2A startup, then verify all 7 real Agent
Cards are reachable:
```bash
for port in 8101 8102 8103 8104 8105 8106 8107; do
  curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:$port/.well-known/agent-card.json
done
# expected: 200 seven times
```

## 3. Inject a real fault and confirm the symptom
```bash
curl -X POST http://localhost:8001/admin/fault/inject \
     -H "Content-Type: application/json" -d '{"fault_type":"bad_deployment"}'
curl http://localhost:8001/admin/state   # bad_deployment: true
curl http://localhost:8001/orders        # ~35% real 500s now
```
Other available `fault_type` values: `db_slowdown`, `config_error`,
`dependency_failure`, `resource_exhaustion` (see `fault_injection/scenarios.py`
for the full 5-scenario catalog and ground truth used by `evaluation/`).

## 4. Run the full investigation — REQUIRES LIVE GROQ CALL
```bash
.venv-orchestrator/Scripts/python orchestrator/run_demo.py \
    "orders endpoint intermittently returning 500s since the last deployment"
```
This calls `orchestrator/investigation.py`'s `run_investigation()` — the same
function `orchestrator/tests/test_investigation_e2e.py` already exercises —
and prints the final persisted incident JSON (findings, hypotheses, critic
verdicts, decision, and — on `DIAGNOSED` — the recovery outcome). It makes
real Groq calls to every diagnostic agent, the Evidence Agent, the
Root-Cause Critic, and (if diagnosed) the Recovery Agent.
**Not run in the Phase 10B session** — no Groq/Gemini quota was spent this
session per explicit instruction. `orchestrator/run_demo.py` itself was
verified this session to import cleanly and parse its CLI arguments
correctly (`--help`); the live LLM round trip is the one piece of this
runbook that still needs a real run against non-exhausted Groq quota before
it can be marked live-verified end-to-end.

## 5. Watch it live in the dashboard
```bash
npm --prefix dashboard run dev
```
Open the incident by ID (printed by step 4, format `INC-xxxxxxxx`) in the
dashboard at `http://localhost:5173`.

## 6. If DIAGNOSED: approve (or reject) the recovery plan
```bash
curl -X POST http://localhost:8000/incidents/<incident_id>/approve \
     -H "Content-Type: application/json" \
     -d '{"decision":"APPROVED","approved_by":"demo-operator"}'
```
`run_demo.py` polls for this up to `MAX_APPROVAL_WAIT_SECONDS` (default 120s)
before giving up with `APPROVAL_EXPIRED`.

## 7. Clean teardown
```bash
curl -X POST http://localhost:8001/admin/fault/clear   # in case the demo aborted early
# stop every uvicorn/a2a_service.py process you started in steps 1-2
```
On Windows, find and stop each by port:
```bash
netstat -ano | grep -E ":800[01]|:810[1-7]" | grep LISTENING
# then: powershell -Command "Stop-Process -Id <pid> -Force"
```
Confirm all 9 ports are free before ending the session.

## What this runbook does NOT cover
- The Phase 9 official 3-arm benchmark across all 5 fault scenarios
  (`evaluation/run_experiment.py`) — separate procedure, see
  `evaluation/CLAUDE.md`, and it is still pending a live run (see
  `docs/PROJECT_STATE.md` "Blockers").
- Docker Compose demo variant — `docker-compose.yml` currently builds/runs
  `backend` + `production` only; the A2A services and dashboard are run
  as local processes, not containerized, as of Phase 10.

## Update 2026-10-13

- Reset the shop between incidents: `curl -X POST http://127.0.0.1:8001/admin/reset` (the dashboard's Inject button does this itself). Old errors and rollbacks otherwise look like evidence in the next incident.
- Restarting the backend also stops the agents it launched; start them again with `POST /demo/agents/start` or the dashboard ON switch.
