# crewai_critic — Local Instructions

## Purpose
The Root-Cause Critic implemented with **CrewAI** and served over real **A2A**, so NEXUS has an ADK<->CrewAI
boundary (course requirements 6 and 7). Folder is NOT called `crewai/` on purpose: that would shadow the package.

## Owned
- `a2a_service.py` — CrewAI `Agent` (DeepSeek via LiteLLM) behind an a2a-sdk 0.3.x server (CrewAI ships no A2A server;
  it only generates cards/clients). Same A2A name/port as the ADK Critic (`root_cause_critic`, 8106), same contract:
  instruction + `build_critique` live in ADK-free `agents/critic/critic_core.py`. Adds `framework: "crewai"`, `usage`
  (CrewAI `usage_metrics` -> budget shape) and `monitoring` (AgentMonitor) to the critique. `CRITIC_STUB=1` = no model call.
- `SPIKE_RESULT.md` — the compatibility spike (read first).

## Run / select
`NEXUS_CRITIC_FRAMEWORK=crewai` (owner env var, read by `backend/app/demo.py`) makes the dashboard's agent ON switch
launch this service from `.venv-crewai` instead of `agents/critic/a2a_service.py`. Default stays ADK.
Manual: `.venv-crewai/Scripts/python crewai_critic/a2a_service.py`.

## Dependencies
Own venv `.venv-crewai` (gitignored): `crewai[a2a]==1.15.28`, `a2a-sdk[http-server]==0.3.26`. The ADK venvs keep
`a2a-sdk==1.1.4`; they interoperate over the wire (verified), they never share a venv.

## Tests
- `.venv-crewai/Scripts/python -m pytest crewai_critic/tests -q` (3, stub, 0 tokens)
- `.venv-orchestrator/Scripts/python -m pytest orchestrator/tests/test_crewai_critic_a2a.py -q` (ADK client -> CrewAI service
  over A2A, stub, 0 tokens; skipped if `.venv-crewai` is missing)

## Status
implemented + tested (stub); verified live twice (2026-10-15, db_slowdown): CrewAI Critic returned SUPPORTED, usage counted.
Not done: CrewAI-native event listener (monitoring is recorded around the call, not per internal step).
