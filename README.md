# NEXUS

Autonomous Multi-Agent Production Failure Investigation & Recovery System.

A controlled academic research/demo system: a simulated production service is
injected with a real (but reversible) failure, an Incident Manager dispatches
independent diagnostic agents over genuine [A2A](https://a2a-protocol.org/)
(separate OS processes, not function calls), each agent gathers evidence only
through real [MCP](https://modelcontextprotocol.io/) diagnostic tools, an
Evidence Agent forms hypotheses, a Root-Cause Critic challenges them in a
bounded re-evaluation loop, and — on a supported diagnosis — a Recovery Agent
proposes a bounded, guardrail-validated, human-approved recovery plan. See
[CLAUDE.md](CLAUDE.md) for the full build rules,
[docs/PROJECT_STATE.md](docs/PROJECT_STATE.md) for current status, and
[NEXUS_PHASE10_PLAN.md](NEXUS_PHASE10_PLAN.md) for the integration/demo/
packaging work tracked in this file's Phase 10.

**Development ownership:** built solely by Deepu. Mukund and Vanshika are
listed as academic team members for the course submission; see root
`CLAUDE.md` section 4 for the project's rule against attributing
implementation work to team members who did not do it.

**Runtime LLM:** DeepSeek `deepseek-chat` (the default/production provider for
every agent). Groq GPT-OSS 120B and Gemini remain available as opt-in
overrides via `NEXUS_LLM_PROVIDER`/`NEXUS_LLM_MODEL` in `.env` — see
`docs/PROJECT_STATE.md`.

## Status at a glance
Phases 1-9 (foundation, observability, ADK/Groq spike, MCP, diagnostic
agents, A2A + orchestration, Evidence Agent + Root-Cause Critic, dashboard,
guardrails + recovery, fault injection + evaluation code) are implemented
and tested. Phase 9's live 3-arm benchmark across all 5 fault scenarios has
not yet been run to completion — blocked on Groq daily-quota headroom, not
on missing code (see `docs/PROJECT_STATE.md` "Blockers"). Phase 10
(integration verification, reproducible demo, documentation, final cleanup)
is in progress — see `NEXUS_PHASE10_PLAN.md`.

Added 2026-10-10: per-incident spending limits (`MAX_LLM_CALLS_PER_INCIDENT`,
`MAX_TOTAL_TOKENS_PER_INCIDENT`, `MAX_TOKENS_PER_AGENT` — when one is reached the
investigation stops and abstains), measured token usage shown on the dashboard, and
incident state saved to a SQLite file so it survives a backend restart. Covered by
deterministic tests; not yet exercised against a live model.

## Quickstart

```bash
docker compose up -d   # backend + simulated production only
```

Backend health: http://localhost:8000/health
Incidents are stored in SQLite (`NEXUS_DB_PATH`; default `backend/.data/nexus.db`, or the
`nexus-data` volume under Docker Compose), so they persist across restarts.
Simulated production health: http://localhost:8001/health

The full multi-agent stack (7 independent A2A agent services + the React
dashboard) currently runs as local processes rather than inside Docker
Compose — see [docs/DEMO_RUNBOOK.md](docs/DEMO_RUNBOOK.md) for the exact,
live-verified, step-by-step procedure to start everything, inject a fault,
and watch an investigation happen end to end.

## Tests

```bash
# backend + production (no extra deps beyond requirements-dev.txt)
pip install -r requirements-dev.txt
pytest

# every other component has its own isolated venv + requirements.txt
# (dependency isolation — see root CLAUDE.md section 23):
#   .venv-mcp/          -> mcp/requirements.txt
#   .venv-agents/        -> agents/requirements.txt
#   .venv-orchestrator/ -> orchestrator/requirements.txt (also covers
#                          guardrails/ and evaluation/)
```
Each component's local `CLAUDE.md` documents its exact test command and
whether it needs live services running first (most do not; the real-A2A and
real-Groq suites are called out explicitly where they exist).

## Dashboard

```bash
npm --prefix dashboard install
npm --prefix dashboard run dev     # http://localhost:5173
```

## Where the test data comes from

NEXUS never touches real production data. It investigates a small **simulated** online
shop (`production/`): 10 invented orders in a SQLite database, plus metrics, logs and
traces produced by real HTTP requests to that service. `fault_injection/` then breaks
it on purpose in one of 5 ways (bad deployment, slow database, config error, dependency
failure, resource exhaustion) by flipping switches inside the simulator — e.g. the
slow-database fault really adds 0.25 s to every query. Because we cause the fault, we
know the correct root cause, and only `evaluation/` is allowed to read that answer key.
This shows the method working on a controlled toy system, not on a real company's
systems. Some faults (e.g. the slow database) leave no signal unless requests hit the
service, so the dashboard's demo button sends real `GET /orders` requests first.

## Packages (dependencies)

A *package* is a ready-made bundle of code someone else wrote that we install instead of
writing it ourselves — e.g. `fastapi` (web server), `google-adk` (agents), `litellm`
(talks to the model), `a2a-sdk` (agent-to-agent protocol), `mcp` (tool protocol). Each
component lists its exact versions in its own `requirements.txt` and installs them into
its own virtual environment (`.venv-agents/`, `.venv-mcp/`, …) so one component's
packages cannot break another's.

## Docs

- [docs/DEMO_GUIDE.md](docs/DEMO_GUIDE.md) (step-by-step live demo, with the shop page)
- [docs/PROJECT_EXPLAINED.md](docs/PROJECT_EXPLAINED.md) (plain-English overview)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/EVENT_SCHEMA.md](docs/EVENT_SCHEMA.md)
- [docs/API_CONTRACT.md](docs/API_CONTRACT.md)
- [docs/EVALUATION.md](docs/EVALUATION.md)
- [docs/DEMO_RUNBOOK.md](docs/DEMO_RUNBOOK.md)
- [docs/PROJECT_STATE.md](docs/PROJECT_STATE.md)
