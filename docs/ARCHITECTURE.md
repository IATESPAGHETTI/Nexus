# NEXUS Architecture

## Layers (must stay separated — see root CLAUDE.md rule 4/17)

```text
Evidence Collection   agents/metrics, agents/logs_traces, agents/change_analysis, agents/database
Reasoning             agents/evidence  (hypothesis synthesis)
Criticism             agents/critic    (Root-Cause Critic)
Orchestration          orchestrator/    (Incident Manager, dispatch, re-evaluation loop)
Recovery              agents/recovery
Safety                guardrails/      (safety validation, sandbox checks, kill switch)
Persistence           backend/         (incident state, event store, API)
Presentation           dashboard/       (reads events/state only, no business logic)
Evaluation             evaluation/, fault_injection/ (never leaks ground truth to agents)
```

Rules:
- Dashboard never contains business logic; it renders state + live events from the backend.
- Agents never mutate infrastructure directly — only through MCP tools in `mcp/`.
- Recovery never bypasses `guardrails/`.
- `evaluation/` owns ground truth; diagnostic agents must never see it.

## High-level flow

```text
Incident -> Incident Manager (orchestrator/)
         -> Parallel Evidence Agents (agents/metrics, logs_traces, change_analysis, database)
              each agent uses mcp/ tools only, emits structured findings
         -> Evidence Agent (agents/evidence) synthesizes findings into hypotheses
         -> Root-Cause Critic (agents/critic) challenges leading hypothesis
         -> Re-evaluation loop (orchestrator/) requests more evidence if needed
         -> Diagnosis reached OR Abstention
         -> Recovery Agent (agents/recovery) proposes bounded plan
         -> guardrails/ safety validation + sandbox check
         -> Human approval (backend/ API + dashboard/)
         -> Controlled execution + verification
```

## Communication

- **A2A — implemented (Phase 5).** Real Agent2Agent protocol via the official
  `a2a-sdk` + `google.adk.a2a.utils.agent_to_a2a.to_a2a()`. Each of the 4
  diagnostic agents runs as its **own OS process** (`agents/<name>/a2a_service.py`,
  own port, see `agents/common/ports.py`), serving a real Agent Card at
  `/.well-known/agent-card.json` and a real JSON-RPC task endpoint. The Incident
  Manager (`orchestrator/incident_manager.py`) never imports a diagnostic agent's
  code — it only holds `google.adk.agents.RemoteA2aAgent` proxies (one per agent,
  resolved from that agent's real Agent Card URL) inside an ADK `ParallelAgent`,
  so dispatch to all 4 is a genuine concurrent network fan-out, not an in-process
  loop. See `docs/API_CONTRACT.md` "A2A protocol (implemented)" for the real
  message/task shapes and `orchestrator/spike/` for why `include_reasoning=False`
  is mandatory on every Groq-backed agent, A2A-served or not.
- **MCP — implemented (Phase 3).** Controlled diagnostic tool calls (metrics,
  logs, traces, git, deployment history, DB diagnostics). Every call is bounded,
  validated, and locally audited (`mcp/audit.py`); the full event-bus bridge
  (`MCP_TOOL_CALL`/`MCP_TOOL_RESULT` on the backend event stream) is Phase 6.
  MCP access is unchanged by the A2A layer: each diagnostic agent's `McpToolset`
  connection lives inside its own A2A service process, exactly as it did when
  invoked directly in Phase 4 — the A2A boundary sits *outside* the MCP boundary,
  never bypassing or replacing it.
- **Events**: every major transition emits a structured event consumed by the backend
  event store and streamed live to the dashboard. Not yet built (Phase 6).

## Status

Phase 5 (A2A + Orchestration) implemented and tested. See `docs/PROJECT_STATE.md`
for current state. Sections below this point describing `evidence/`, `critic/`,
`recovery/`, `guardrails/`, `dashboard/`, `evaluation/` remain target architecture
— not yet built.
