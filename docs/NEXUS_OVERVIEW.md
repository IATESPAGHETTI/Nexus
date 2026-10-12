# NEXUS — Project Overview (for a new Claude chat)

> Paste or point a fresh Claude session at this file to get oriented fast.
> It is a **summary**. The authoritative sources are root `CLAUDE.md` (rules),
> `docs/PROJECT_STATE.md` (current state / history), and each component's local
> `CLAUDE.md`. If this file disagrees with them, they win.

---

## 1. What NEXUS is

**NEXUS** = *Autonomous Multi-Agent Production Failure Investigation & Recovery System.*

A controlled academic research/demo system. A simulated production service has a
fault injected into it; a team of independent AI agents investigates the incident
using real diagnostic tools, argues about the root cause, and either reaches a
**supported diagnosis** or **explicitly abstains**. If diagnosed, a Recovery Agent
proposes a bounded fix that must pass safety validation and **human approval**
before a controlled executor applies it. The whole thing is observable in a live
React dashboard and is scored against ground truth in a repeatable evaluation.

It is **not** a chatbot. It is not connected to any real production system.

- **Owner / sole active developer:** Deepu. Mukund and Vanshika are listed on the
  academic submission only — never attribute implementation work to them.
- **Stack:** Python + FastAPI backend, Google ADK (agent framework), real A2A
  (`a2a-sdk`), real MCP (`mcp` SDK), LiteLLM, React + TypeScript + Vite dashboard,
  Docker Compose (backend + production only).
- **Runtime LLM:** currently defaults to **DeepSeek** (`deepseek/deepseek-chat`),
  changed 2026-09-19. Groq GPT-OSS 120B (`groq/openai/gpt-oss-120b`) and Gemini are
  opt-in via `NEXUS_LLM_PROVIDER` / `NEXUS_LLM_MODEL`. Note: root `CLAUDE.md` still
  describes Groq/GPT-OSS as the runtime model; `runtime_config.py` +
  `docs/PROJECT_STATE.md` reflect the newer DeepSeek default. Claude Code (the
  development tool) is completely separate from the runtime model.
- Keys live only in the local `.env` (never printed, logged, or committed).

## 2. The core idea (how an investigation flows)

```
Fault injected into simulated production
        ↓
Incident Manager creates incident, fans out (real A2A, in parallel) to 4 diagnostic agents
        ↓
Each agent calls MCP diagnostic tools → structured Findings (observation vs. interpretation)
        ↓
Evidence Agent turns Findings into explicit Hypotheses (with evidence IDs)
        ↓
Root-Cause Critic challenges the leading hypothesis
   ├─ SUPPORTED             → DIAGNOSED
   ├─ CONTRADICTED          → reject, try next hypothesis
   ├─ INSUFFICIENT_EVIDENCE / REQUEST_MORE_EVIDENCE
   │                        → second-round A2A dispatch for more evidence, regenerate hypotheses, loop
   └─ ABSTAIN               → ABSTAINED
        ↓ (bounded by MAX_REEVALUATION_LOOPS, default 3; exhaustion ⇒ ABSTAINED, never a forced guess)
DIAGNOSED → Recovery Agent → safety validation → human approval → guarded execution → verification → RESOLVED
```

Evidence-first: agents never guess a root cause from the incident text. Every
hypothesis tracks supporting/contradicting evidence IDs, and IDs the model invents
are dropped in code (`build_hypotheses`), not trusted.

## 3. The agents — what each one does

There are **7 agents**, each its own **independent OS process / A2A service**
on its own port (`agents/common/ports.py`). The Incident Manager reaches them
only over real network A2A calls — never by importing them.

| Agent | Port | Role | Tools |
|---|---|---|---|
| **Incident Manager** | — (orchestrator, `orchestrator/incident_manager.py`) | Creates incident state; builds an ADK `ParallelAgent` of `RemoteA2aAgent` proxies and dispatches to the 4 diagnostic agents concurrently; collects their Findings. Drives the bounded loop in `orchestrator/investigation.py`. | A2A clients only |
| **Metrics Agent** | 8101 | Looks at error rate, latency, request volume — *is something degraded, and how badly?* | MCP `get_metrics` |
| **Logs & Traces Agent** | 8102 | Reads application logs and request traces — *what errors/exception types, on which endpoints?* | MCP `query_logs`, `get_trace` |
| **Change Analysis Agent** | 8103 | Looks at deployment/change history and bounded git diffs — *did something change right before the failure?* | MCP `get_recent_deployments`, `get_git_diff` |
| **Database Agent** | 8104 | Inspects query timings / slow queries / DB health — *is the database the bottleneck?* | MCP `get_database_stats` |
| **Evidence Agent** | 8105 | Reasons over the Findings (no tools) and emits structured **Hypotheses** with supporting/contradicting evidence IDs, confidence (clamped 0–1), and missing evidence. | none |
| **Root-Cause Critic** | 8106 | Adversarial reviewer (no tools). Hunts for contradictions, unsupported assumptions, alternative explanations; returns a verdict (`SUPPORTED`/`CONTRADICTED`/`INSUFFICIENT_EVIDENCE`/`REQUEST_MORE_EVIDENCE`/`ABSTAIN`) and what evidence to fetch next. Garbled/out-of-enum verdicts normalize to `INSUFFICIENT_EVIDENCE`. | none |
| **Recovery Agent** | 8107 | Proposes a bounded recovery plan from the 4 allowlisted actions only. **Cannot execute anything.** Must copy a real `target_version` from evidence for rollbacks; invented actions are dropped. | none |

Diagnostic agents are built on `agents/common/diagnostic_agent.py` (one ADK `Agent`
each, MCP stdio connection, structured `Finding` output). Evidence/Critic/Recovery
use `agents/common/reasoning_agent.py` (LLM-only, no tools). Each agent is served
over A2A by `agents/common/a2a_server.py`, which also publishes a real Agent Card at
`/.well-known/agent-card.json`.

### Non-agent components that matter
- **MCP server** (`mcp/`): 7 real tools over stdio — `get_metrics`, `query_logs`,
  `get_trace`, `get_recent_deployments`, `get_git_diff`, `get_database_stats`,
  `run_diagnostic`. Bounded, validated, audited, never raise. Agents get evidence
  *only* through these — no arbitrary file/SQL/shell access.
- **Production simulation** (`production/`, port 8001): FastAPI service with real
  metrics/logs/traces/DB diagnostics/change history/orders, plus mutable fault
  state (`state.py`) and `/admin/*` endpoints for fault injection and recovery.
- **Backend** (`backend/`, port 8000): FastAPI incident state + event store. Persistence
  only — no business logic. `POST /incidents`, `GET /incidents/{id}`,
  `/incidents/{id}/events`, `/state`, `/approve`, plus `/demo/*` for the dashboard button.
- **Guardrails** (`guardrails/`): the safety layer — one authoritative allowlist of
  4 actions (`restart_service`, `rollback_deployment`, `reset_config`,
  `scale_resources`), a deterministic non-LLM `validate_plan()` that rejects the whole
  plan on any violation, a file-based kill switch re-checked before *every* action,
  and an audit log. LLM output is never executed as shell.
- **Orchestrator** (`orchestrator/`): `investigation.py` (bounded loop),
  `recovery.py` (propose → validate → approve → execute → verify), `event_bridge.py`
  (pushes events to backend), `remote_call.py` (generic real-A2A call), `run_demo.py` (CLI).
- **Fault injection** (`fault_injection/`): 5 scenarios with ground truth —
  `FI-bad-deployment`, `FI-db-slowdown`, `FI-config-error`, `FI-dependency-failure`,
  `FI-resource-exhaustion`. Ground truth is hidden from agents.
- **Evaluation** (`evaluation/`): compares 3 arms on the same fault — single-agent
  baseline, full NEXUS, NEXUS without critic — and scores against ground truth.
- **Dashboard** (`dashboard/`): "live command center" — Mission Control home
  (real system status + "Inject Controlled Failure" button), investigation page with
  agent canvas, A2A stream, MCP activity, hypothesis panel, critic panel, decision
  (diagnosis/abstention shown with equal weight), and a recovery panel with real
  Approve/Reject. Everything is derived from the real event log — no mock data.

## 4. Hard rules to respect (from root CLAUDE.md)

1. **No faking.** Don't label Python function calls as A2A/MCP/multi-agent. If it's
   called implemented, it must run and be tested.
2. **Preserve working code.** Read the local `CLAUDE.md` first, make the smallest
   change, re-run tests, update `docs/PROJECT_STATE.md`.
3. **Precise status words:** `implemented + tested`, `implemented + not yet tested`,
   `planned`, `blocked`, `partially implemented`. Never say "works" unverified.
4. **Keep context small.** Don't read the whole repo. Order: root `CLAUDE.md` →
   `docs/PROJECT_STATE.md` → component `CLAUDE.md` → relevant docs → only needed source.
5. **Secrets:** never print/log/commit API keys; `.env` stays gitignored.
6. **Dependency isolation:** separate venvs per component (`.venv`, `.venv-mcp`,
   `.venv-agents`, `.venv-orchestrator`); don't install ADK/LiteLLM/MCP into the
   backend/production env.
7. **Abstention is a valid outcome.** Never force a diagnosis; never weaken tests or
   silently swap the model/provider to hide failures.
8. **Recovery is never unrestricted:** allowlist → deterministic validation → human
   approval → guarded execution → verification. Kill switch always available.
9. **Never fabricate metrics or contributions.** Report only measured values.

## 5. Current status (as of the last `PROJECT_STATE.md` update, 2026-09-19)

| Phase | Status |
|---|---|
| 1 Foundation, 2 Observability | implemented + tested (Docker verified) |
| 2.5 ADK/Groq spike | passed (needs `include_reasoning=False` on Groq) |
| 3 MCP (7 tools) | implemented + tested |
| 4 Four diagnostic agents | implemented + tested |
| 5 Real A2A + Incident Manager | implemented + tested (separate processes verified via netstat) |
| 6 Evidence Agent, Critic, bounded loop, backend event store | implemented + tested |
| 7 Dashboard (later redesigned as live command center) | implemented + build-verified + live-checked |
| 8 Guardrails + Recovery | implemented + tested |
| 9 Fault injection + Evaluation code | implemented + unit-tested |
| 10 Integration / demo / docs / cleanup | done, with two items flagged below |

**Honest open items:**
- The **official 3-arm benchmark** across all 5 scenarios has **not** been run live.
  Earlier it was blocked by Groq's free-tier daily quota; the provider has since been
  switched to DeepSeek by default, and only a single-agent DeepSeek → ADK → MCP smoke
  test has passed (2026-09-19).
- A **full live `orchestrator/run_demo.py` investigation** on the current provider has
  not been recorded as verified end-to-end. An earlier live run with Groq abstained
  because rate limits made all 4 diagnostic agents fail (honestly reported as such).
- **Docker Compose** runs only `backend` + `production`; A2A services and dashboard run
  as local processes.
- LLM usage panel (updated 2026-10-10): per-incident model calls/tokens are now
  measured from what each agent reports and shown against NEXUS's own spending
  limits (`orchestrator/budget.py`); the provider's remaining quota is still
  "Unavailable from provider". Not yet counted: Recovery Agent and post-fix
  verification calls. Not yet exercised against a live model (no working key).
- Incidents are now saved to a SQLite file and survive a backend restart (verified
  with a real server restart; Docker volume config validated but not run).
- The git tree has many uncommitted changes on top of a single initial commit
  (`c8b2327`).

Last recorded deterministic test counts (see PROJECT_STATE for detail), re-run
2026-10-10: backend + production 35, fast agents 32, orchestrator 40 (+ guardrails 14),
evaluation 16, fault-injection scenarios 5 (pure tests). MCP (22) and the live
fault-injection tests were not re-run in that pass.

## 6. How to run it

Prereqs: `.env` at repo root with the key for the chosen provider (e.g.
`DEEPSEEK_API_KEY`); the four venvs built; ports 8000, 8001, 8101–8107 free.
Full procedure: **`docs/DEMO_RUNBOOK.md`**. Short version:

```bash
# 1. production + backend
cd production && ../.venv/Scripts/python -m uvicorn service:app --port 8001 &
cd backend    && ../.venv/Scripts/python -m uvicorn app.main:app --port 8000 &

# 2. all 7 A2A agent services (one process each)
.venv-agents/Scripts/python agents/<metrics|logs_traces|change_analysis|database|evidence|critic|recovery>/a2a_service.py &

# 3. inject a fault
curl -X POST localhost:8001/admin/fault/inject -H "Content-Type: application/json" -d '{"fault_type":"bad_deployment"}'

# 4. run the investigation (spends real LLM calls)
.venv-orchestrator/Scripts/python orchestrator/run_demo.py "orders endpoint intermittently returning 500s"

# 5. dashboard
npm --prefix dashboard run dev      # http://localhost:5173
```

Tests (per component, each in its own venv — see the local `CLAUDE.md`), e.g.:

```bash
.venv/Scripts/python -m pytest                                             # backend + production
.venv-agents/Scripts/python -m pytest agents/tests/test_evidence_critic.py # fast agent tests
.venv-orchestrator/Scripts/python -m pytest orchestrator/tests/test_investigation_logic.py
```

## 7. Where to look next

| Need | File |
|---|---|
| Rules & definition of done | `CLAUDE.md` |
| Current state, history, known issues | `docs/PROJECT_STATE.md` (long — read the top, grep the rest) |
| Architecture / A2A topology | `docs/ARCHITECTURE.md` |
| HTTP + schema contracts | `docs/API_CONTRACT.md` |
| Event types | `docs/EVENT_SCHEMA.md` |
| Evaluation design | `docs/EVALUATION.md` |
| Demo procedure | `docs/DEMO_RUNBOOK.md` |
| Phase 10 plan | `NEXUS_PHASE10_PLAN.md` |
| Per-component notes | `<component>/CLAUDE.md` |
| Provider selection | `runtime_config.py` |
