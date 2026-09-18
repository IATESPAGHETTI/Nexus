# NEXUS Project State

## Current Phase
Phase 6: Evidence Agent + Root-Cause Critic + bounded re-evaluation loop —
implemented + tested.

## Current Task
Phase 6 complete, explicitly authorized by the user (previous session had
stopped after Phase 5 pending exactly this go-ahead). A cleanup pass was
performed after Phase 6 (removed stray `__pycache__`/`.pytest_cache` dirs,
killed all 6 A2A service processes, brought Docker containers down, verified
`git status`/no tracked secrets — see "Handoff verification" below). STOPPED
per root CLAUDE.md's phase discipline — do not start Phase 7 (dashboard),
Phase 8 (recovery/guardrails), or Phase 9 (fault injection/evaluation) until
the user asks.

## Completed
### Phase 1: Foundation
- Git repo initialized at repo root.
- Repository structure created (`docs/`, `backend/`, `orchestrator/`, `agents/{metrics,
  logs_traces,change_analysis,database,evidence,critic,recovery}`, `mcp/`, `guardrails/`,
  `production/`, `fault_injection/`, `evaluation/`, `dashboard/`, `tests/`).
- Root `CLAUDE.md` + local `CLAUDE.md` in every top-level component folder.
- `docs/ARCHITECTURE.md`, `docs/EVENT_SCHEMA.md`, `docs/API_CONTRACT.md`,
  `docs/EVALUATION.md` created as the initial contracts.
- `backend/` — minimal FastAPI app (`app/main.py`) with `GET /health`.
- `docker-compose.yml` builds and runs backend + production with healthchecks.
- `requirements-dev.txt`, `pytest.ini`, `.gitignore`, `README.md`.

### Phase 2: Observability
- `production/observability.py` — thread-safe in-process `MetricsStore`, `LogStore`,
  `TraceStore`, `QueryStore` (real data recorded from real requests, ring-buffered).
- `production/db.py` — seeded in-memory SQLite `orders` table; every query timed and
  recorded into `QueryStore`.
- `production/changes.py` — static simulated deployment/change history (3 seed entries).
- `production/service.py` — request-observing middleware (adds `X-Trace-Id`, records
  metrics/logs/traces per request) + endpoints: `/metrics`, `/logs`, `/traces`,
  `/traces/{id}`, `/changes`, `/db/diagnostics`, `/orders`, `/orders/{id}`.
- `docs/API_CONTRACT.md` updated with the full production HTTP API.
- `production/CLAUDE.md` updated to describe the new modules/contract.
- `tests/test_observability.py` — 6 new tests covering metrics, logs, trace
  roundtrip/404, change history ordering, orders + db diagnostics.

### Architecture decision: Google ADK adopted for orchestration/A2A
User evaluated ADK vs. a hand-rolled orchestrator and directed adoption of
**Google ADK (Python)** as the agent framework, gated by a mandatory compatibility
spike. A full master `CLAUDE.md` (v2) was supplied and is now the root `CLAUDE.md`
(Phase 1/2 content preserved unchanged; only the orchestration-framework direction
and process are new).

### Phase 2.5: ADK/Groq compatibility spike — implemented + tested, PASS
- Isolated venv `.venv-orchestrator/` created (never installed into the shared
  `backend`/`production` venv) per root CLAUDE.md section 23.
- `orchestrator/spike/adk_groq_spike.py` — builds one ADK `Agent` with
  `LiteLlm(model="groq/openai/gpt-oss-120b", include_reasoning=False)`, gives it one
  trivial tool returning a fixed non-guessable value, runs it via `InMemoryRunner`,
  and asserts: model responded, tool was actually called, tool result appeared in
  the event stream, and the tool result appeared correctly in the model's final
  answer. **Result: PASS** — real Groq call, real tool call, real result round-trip.
- `orchestrator/spike/SPIKE_RESULT.md` — full writeup, including a real blocking bug
  found and fixed: Groq's GPT-OSS models attach `reasoning_content` to responses;
  ADK/LiteLLM echo it back on the next tool-calling turn and Groq's own schema
  rejects it. Fix: `LiteLlm(..., include_reasoning=False)`. `litellm.drop_params =
  True` does NOT fix it. **Mandatory for every future Groq-backed ADK agent.**

### Phase 3: MCP — implemented + tested
Real MCP diagnostic server (`mcp.server.mcpserver.MCPServer`, stdio transport,
`mcp` SDK 2.2.0) exposing 7 tools, all reaching evidence only through the Phase 2
production HTTP API or (for `get_git_diff`) this repo's own bounded/allowlisted git
history — no arbitrary filesystem/shell/SQL access, no secrets touched.

- `mcp/config.py`, `mcp/production_client.py`, `mcp/git_diff_tool.py`, `mcp/audit.py`
  — config/HTTP client/git access/local audit log, all bounded and allowlisted.
- `mcp/tools.py` — the 7 tools (`get_metrics`, `query_logs`, `get_trace`,
  `get_recent_deployments`, `get_git_diff`, `get_database_stats`, `run_diagnostic`),
  each validated, bounded, audited, returning `{"ok": bool, ...}`, never raising.
- `mcp/server.py` — registers all 7 tools with `structured_output=True` on a real
  `MCPServer` (stdio).
- Isolated venv `.venv-mcp/`. 22 tests (16 unit + 5 real-protocol + 1 audit).

### Phase 4: Independent Diagnostic Agents — implemented + tested
4 independent ADK `Agent`s, each with ONE responsibility, each reaching evidence
**only** through the real Phase 3 MCP server, each using GPT-OSS 120B via Groq
with `include_reasoning=False`.

- `agents/common/mcp_connection.py`, `agents/common/finding.py`,
  `agents/common/diagnostic_agent.py` — MCP stdio connection factory, Finding
  builder (observation/interpretation split enforced structurally), and
  `DiagnosticAgent` class (builds the ADK Agent, runs it, collects evidence).
- `agents/metrics/agent.py`, `agents/logs_traces/agent.py`,
  `agents/change_analysis/agent.py`, `agents/database/agent.py` — the 4 agents,
  each exporting `investigate(question) -> Finding dict`.
- Isolated venv `.venv-agents/`. Package `__init__.py`s added throughout `agents/`
  so the 4 same-named `agent.py` modules don't collide when imported together.
- 13 tests (`test_finding.py` + `test_agents_integration.py`) as of Phase 4;
  `test_finding.py` grew to 8 in Phase 5 (see below).

### Phase 5: Genuine A2A + Orchestration — implemented + tested
Real [Agent2Agent protocol](https://a2a-protocol.org/) (`a2a-sdk==1.1.4` +
`google.adk.a2a`), NOT Python function calls. Each of the 4 diagnostic agents now
also runs as its own independent A2A service (separate OS process, separate
port); the Incident Manager reaches them only through real network A2A calls.
Full detail: `docs/API_CONTRACT.md` "A2A protocol (implemented)".

- `agents/common/ports.py` — port registry (metrics=8101, logs_traces=8102,
  change_analysis=8103, database=8104) + Agent Card URL / base URL helpers.
- `agents/common/a2a_server.py` — `DiagnosticAgentExecutor` (real
  `a2a.server.agent_execution.AgentExecutor` subclass): for each real incoming
  A2A task, enqueues a `Task` (state machine `SUBMITTED` -> `WORKING` ->
  `COMPLETED`, matching what the a2a-sdk server actually requires — see Known
  Issues), runs the SAME `DiagnosticAgent.investigate()` as Phase 4, and
  completes the task with the resulting Finding JSON-encoded as the agent
  message. `build_a2a_app(diagnostic_agent, host, port)` wraps this with ADK's
  `to_a2a()`, which also auto-builds a real Agent Card from the agent's
  name/description/tools.
- `agents/common/remote_agent.py` — `build_remote_agent(name, description)`
  returns a real `google.adk.agents.RemoteA2aAgent` (ADK's A2A client proxy),
  resolved from that agent's real Agent Card URL.
- `agents/<name>/a2a_service.py` (x4) — standalone launcher per agent:
  `.venv-agents/Scripts/python agents/<name>/a2a_service.py`, each its own
  `uvicorn` process on its own port. Verified via `netstat` that all 4 are
  independently listening, separate PIDs — genuinely separate processes, not
  in-process objects.
- `agents/common/diagnostic_agent.py` updated: `_build_adk_agent` renamed to
  public `build_adk_agent()` (reused by both the direct Phase 4 path and the new
  A2A executor); `description` param added (flows into the Agent Card); each
  `DiagnosticAgent` now carries `default_question`; `litellm.num_retries = 5` set
  module-wide (see Known Issues — real Groq rate-limit fix).
- `orchestrator/incident_manager.py` — **new**. `build_incident_manager(agent_names=None)`
  builds an ADK `ParallelAgent` whose `sub_agents` are `RemoteA2aAgent` proxies
  (real network clients, never direct imports) for the named diagnostic agents
  (all 4 by default). `investigate_incident(text, agent_names=None)` runs it via
  `InMemoryRunner`, parses each agent's real A2A response JSON, and returns
  `{"findings", "a2a" (task_id/context_id per agent), "agents_dispatched",
  "agents_responded"}`. `ParallelAgent` genuinely dispatches to all sub-agents
  concurrently — verified: 4 real, distinct A2A task IDs in flight at once.
- `agents/common/finding.py` — confidence-marker regex fixed to tolerate markdown
  emphasis (`**CONFIDENCE:** 0.68`, a real model output variant hit while running
  Phase 5's fuller test suite) in addition to the plain `CONFIDENCE: 0.68` form
  Phase 4's regex expected. New regression test added.
- `agents/tests/test_a2a.py` — **new**, 6 tests: Agent Card accessibility
  (parametrized over all 4 agents, asserts name + tool-derived skill IDs), a real
  `RemoteA2aAgent` request/response round trip against the metrics agent with
  protocol-level assertions (`event.custom_metadata['a2a:task_id']`,
  `['a2a:context_id']`, `['a2a:response']['status']['state'] ==
  'TASK_STATE_COMPLETED'`), MCP-evidence-present assertion (proves MCP still
  works inside the receiving agent), and a distinct-task-id-per-request test.
- `orchestrator/tests/test_incident_manager.py` — **new**, 2 tests: a 2-agent
  parallel dispatch (asserts distinct real task/context IDs per agent) and a
  full 4-agent parallel dispatch (tolerant of the Groq TPM limit: asserts >=3/4
  respond rather than a hard 4/4, so the test isn't flaky on an external quota).
- `docs/ARCHITECTURE.md`, `docs/API_CONTRACT.md`, `agents/CLAUDE.md`,
  `orchestrator/CLAUDE.md` all updated with the real, implemented A2A shapes.
- `agents/requirements.txt`, `orchestrator/requirements.txt` — added
  `a2a-sdk==1.1.4`, `opentelemetry-api==1.42.1` (pinned down to satisfy
  `google-adk`'s constraint after `a2a-sdk` pulls a newer one — see Known Issues).

### Phase 6: Evidence Agent + Root-Cause Critic + bounded re-evaluation loop — implemented + tested
Reused Phase 4/5 infrastructure wherever it already fit (no rewrite of
`diagnostic_agent.py`, `a2a_server.py`, `finding.py`, `incident_manager.py`,
`mcp/`, `production/`) and added exactly the new pieces Phase 6 needed:

- `agents/common/reasoning_agent.py` — **new**. `ReasoningAgent`: same
  Groq/`LiteLlm` (`include_reasoning=False`) build as `DiagnosticAgent` but with
  **no tools** — the Evidence Agent and Root-Cause Critic only ever reason over
  JSON they're handed, never call out for evidence themselves. Also owns
  `extract_json()` (tolerant fenced-block/plain-JSON extraction from the
  model's reply; returns `None`, never raises, on unparseable text).
- `agents/evidence/agent.py`, `agents/evidence/a2a_service.py` — **new**.
  Evidence Agent (port 8105). `build_hypotheses()` is the Python-side
  structural enforcement mirroring `finding.py`'s `build_finding()`:
  `hypothesis_id` always assigned here (never trusted from the model),
  confidence clamped to `[0, 1]`, and any `supporting_evidence_ids`/
  `contradicting_evidence_ids` the model claims that don't actually exist in
  the input Findings are dropped (counted in `dropped_invented_evidence_ids`,
  never recorded as fact). Served over real A2A by the SAME
  `agents/common/a2a_server.py` used for the 4 diagnostic agents (duck-typed:
  `build_adk_agent()`/`default_question`/async `investigate()`).
- `agents/critic/agent.py`, `agents/critic/a2a_service.py` — **new**.
  Root-Cause Critic (port 8106). `build_critique()`: an unparseable or
  out-of-enum `verdict` is never trusted at face value — normalized to
  `INSUFFICIENT_EVIDENCE` so the loop asks for more evidence rather than
  silently treating a garbled reply as support/contradiction. Same real-A2A
  serving mechanism as above.
- `agents/common/ports.py` — extended (not replaced): added
  `evidence_agent=8105`, `root_cause_critic=8106` to the existing
  `A2A_PORTS` registry.
- `orchestrator/remote_call.py` — **new**. `call_remote_agent(agent_name,
  description, message_text)`: builds a `RemoteA2aAgent` and runs it directly
  through `InMemoryRunner` (the same mechanism `agents/tests/test_a2a.py`
  already proved works for a bare `RemoteA2aAgent`) — generic single-agent
  real-A2A call, reused for both the Evidence Agent and Critic. Never a direct
  import of `agents/evidence/agent.py` or `agents/critic/agent.py`.
- `orchestrator/event_bridge.py` — **new**. Real `httpx` client to
  `backend/`'s `/incidents*` endpoints (`NEXUS_BACKEND_URL`, default
  `http://127.0.0.1:8000`). This is the "bridge `mcp/audit.py` + ADK/A2A events
  into the backend event store" mechanism required by Phase 6 — see its module
  docstring and "Known limitations" below for exactly what is and isn't bridged.
- `orchestrator/investigation.py` — **new**. `run_investigation(incident_description,
  agent_names=None, max_loops=None) -> dict`: the full bounded re-evaluation
  loop. Creates a real incident in `backend/`, dispatches to diagnostic agents
  (reusing `incident_manager.investigate_incident` unchanged), calls the
  Evidence Agent over real A2A for Hypotheses, then loops up to
  `MAX_REEVALUATION_LOOPS` (env var, default 3) calling the Critic over real
  A2A on the leading open hypothesis: `SUPPORTED` -> `DIAGNOSED`;
  `CONTRADICTED` -> reject, try next hypothesis (same loop budget);
  `INSUFFICIENT_EVIDENCE`/`REQUEST_MORE_EVIDENCE` -> real second-round A2A
  dispatch to diagnostic agents for more evidence, hypotheses regenerated,
  loop continues if budget remains; `ABSTAIN` -> `ABSTAINED`. Loop exhaustion
  without `SUPPORTED`/`ABSTAIN` also resolves to `ABSTAINED` — a diagnosis is
  never forced. Every transition persisted to `backend/` via `event_bridge.py`.
- `backend/app/incident_store.py` — **new**. Thread-safe in-memory incident
  state + event store (same `Lock`+`dict` pattern as
  `production/observability.py`), implementing the incident-state field set
  from root CLAUDE.md section 15 and the event envelope from
  `docs/EVENT_SCHEMA.md`.
- `backend/app/main.py` — extended: `POST /incidents`, `GET /incidents/{id}`,
  `POST /incidents/{id}/state`, `POST /incidents/{id}/events`,
  `GET /incidents/{id}/events`.
- `agents/tests/test_evidence_critic.py` — **new**, 13 fast unit tests
  (`build_hypotheses`, `build_critique`, `extract_json`), no network.
- `agents/tests/test_a2a.py` — `test_agent_card_is_accessible`'s parametrize
  fixed to scope to the 4 diagnostic agents only (`AGENT_TOOL_ALLOWLISTS`
  keys) instead of `list(A2A_PORTS)` — adding `evidence_agent`/
  `root_cause_critic` to the shared port registry had silently widened this
  Phase 5 test's parametrize to include them, and it asserted against a
  tool-allowlist dict that (correctly) has no entry for either, since neither
  carries MCP tools. Caught by running the full regression suite; fixed by
  scoping the parametrize back to its original intent (see Known Issues).
- `tests/test_incidents.py` — **new**, 6 `TestClient` tests for the backend
  incident/event endpoints, no network.
- `orchestrator/tests/test_investigation_logic.py` — **new**, 4 deterministic
  tests of `run_investigation`'s control flow with the two real-A2A boundaries
  (`investigate_incident`, `call_remote_agent`) and `event_bridge` monkeypatched:
  SUPPORTED-on-first-loop, CONTRADICTED-then-ABSTAIN (proves the reject-and-
  try-next-hypothesis path), zero-hypotheses-abstains-immediately, and
  max-loop-exhaustion-abstains (proves the bound is real: critic call count
  asserted to never exceed `max_loops`).
- `orchestrator/tests/test_investigation_e2e.py` — **new**, 1 real end-to-end
  test: real A2A dispatch to 2 diagnostic agents -> real A2A to the real
  Evidence Agent -> real A2A to the real Root-Cause Critic, bounded loop,
  asserts a valid bounded decision, real evidence-id provenance on every
  hypothesis, and — via a second independent real HTTP fetch of
  `GET /incidents/{id}/events` — that the required event types actually landed
  in the real backend event store. Also asserts no `GROQ_API_KEY`/`gsk_` ever
  appears in persisted incident state. Ran successfully first try: reached a
  real `ABSTAINED` decision (`"no open hypothesis left to evaluate"`, 2/2
  loops used) after the Evidence Agent produced 1 hypothesis on the first
  round (critic: `INSUFFICIENT_EVIDENCE`) and 0 hypotheses on the regenerated
  second round — a genuine abstention through the real system, not a stubbed
  one.
- `agents/requirements.txt` — unchanged (Evidence/Critic reuse exactly the
  packages the 4 diagnostic agents already had).
- `orchestrator/requirements.txt` — added `httpx==0.28.1` (was already present
  transitively via `a2a-sdk` at this exact version; now pinned explicitly
  since `event_bridge.py`/`remote_call.py` use it directly). Reinstalling with
  this pin present caused pip's resolver to also settle on `google-api-core==2.34.0`
  instead of the previously-installed `2.38.0` (both satisfy `a2a-sdk`'s
  `>=1.26.0` constraint) — verified benign: `RemoteA2aAgent`/`ParallelAgent`/
  `InMemoryRunner` import and the full real-A2A test suite still pass.
- `docs/API_CONTRACT.md` — added the incident-state+event-store HTTP API,
  the Hypothesis schema example (was previously illustrative-only), the new
  Critique schema, the Phase 6 A2A topology entries, and the re-evaluation
  loop contract.
- `docs/EVENT_SCHEMA.md` — status updated: implemented, with the exact list of
  event types actually emitted vs. still-planned (recovery/approval/
  verification, Phase 8).
- `agents/CLAUDE.md`, `orchestrator/CLAUDE.md`, `backend/CLAUDE.md` — updated
  to describe the real, implemented Phase 6 shapes.

## In Progress
Nothing in flight. Stopped after Phase 6 per root CLAUDE.md's phase discipline.

## Next
- Phase 7 (per root CLAUDE.md's implementation order, "Dashboard"): live
  investigation UI (React, per root CLAUDE.md header) consuming
  `backend/`'s `/incidents/{id}` and `/incidents/{id}/events` — currently
  poll-only; SSE/websocket streaming for a *live* dashboard is part of this
  phase, not yet built.
- Phase 8 ("Guardrails + Recovery"): Recovery Agent, safety validation, human
  approval (`POST /incidents/{id}/approve`, still just a stub in
  `docs/API_CONTRACT.md`), sandboxed execution, kill switch.
- Consider whether NEXUS's own application-level token/call budgets (root
  CLAUDE.md section 8: `MAX_TOKENS_PER_AGENT`, `MAX_LLM_CALLS_PER_INCIDENT`,
  `MAX_TOTAL_TOKENS_PER_INCIDENT`) should land before real multi-incident/
  concurrent-agent load. Phase 6 implemented `MAX_REEVALUATION_LOOPS` (the one
  bound the Phase 6 requirements explicitly asked for) but NOT the token/call
  budgets — the Groq TPM limit has now been hit at the single-agent (Phase 4),
  parallel-dispatch (Phase 5), and re-evaluation-loop (Phase 6) levels;
  `litellm.num_retries` absorbs it today but a real budget layer would be more
  deliberate. Explicitly deferred, not overlooked.
- The Incident Manager and the Phase 6 re-evaluation loop are not yet exposed
  as A2A services themselves (`orchestrator/` is an A2A client only) — revisit
  if a future phase needs something else to call them over A2A too.
- `backend/app/incident_store.py` is in-memory only (resets on process
  restart) — fine for Phase 6's single-process demo scope; revisit if
  multi-process backend or restart-durability is ever needed (no current
  requirement for it).
- Dashboard LLM usage panel (root CLAUDE.md section 8: tokens used, rate-limit
  info from Groq response headers) is not implemented — no token/usage
  metadata is currently captured anywhere in the Phase 6 pipeline. Deferred to
  Phase 7 alongside the dashboard itself.

## Known Issues
- **`agents/tests/test_a2a.py::test_agent_card_is_accessible`'s parametrize
  silently widened when Phase 6 added agents to the shared `A2A_PORTS`
  registry:** it was parametrized over `list(A2A_PORTS)` (all A2A services)
  but asserted against `AGENT_TOOL_ALLOWLISTS` (only the 4 diagnostic agents'
  MCP tools) — adding `evidence_agent`/`root_cause_critic` to `A2A_PORTS`
  (agents/common/ports.py) made it try to look up a non-existent allowlist
  entry for them and fail with a `KeyError`. **Fix applied:** parametrize
  changed to `list(AGENT_TOOL_ALLOWLISTS)` instead, scoping the test back to
  its original intent (diagnostic agents' MCP-tool-derived skills) — the
  Evidence Agent's and Critic's real Agent Card/A2A behavior is covered by
  `orchestrator/tests/test_investigation_e2e.py` instead, which reaches them
  the same way production code does (`RemoteA2aAgent`, not a raw Agent Card
  fetch). Caught by running the full `agents/tests` regression suite before
  reporting Phase 6 complete, not by guessing it would be fine.
- **Groq free-tier TPM rate limit — hit at both Phase 4 (single-agent) and
  Phase 5 (4-way parallel dispatch) levels:** `openai/gpt-oss-120b` is limited to
  8000 tokens/min on the current Groq account, shared across all agents. A
  4-agent parallel A2A dispatch is inherently more likely to burst past this than
  sequential calls. **Fix applied:** `agents/common/diagnostic_agent.py` sets
  `litellm.num_retries = 5` (LiteLLM's built-in retry-with-backoff), which
  resolved a reproducible failure (a 4-agent dispatch that got 0-3/4 responses
  without it consistently got 4/4 with it, verified across multiple runs during
  implementation). Additionally, real-LLM tests are paced (8-10s autouse fixture
  delays) in both `agents/tests/test_a2a.py` and
  `orchestrator/tests/test_incident_manager.py`. This remains an external account
  quota, not a NEXUS defect.
- **a2a-sdk server requires an explicit `Task` event before any
  `TaskStatusUpdateEvent`:** `TaskUpdater.submit()` alone (without first
  enqueueing an `a2a.types.a2a_pb2.Task(...)`) raised "Agent should enqueue Task
  before TaskStatusUpdateEvent event" — not documented in the method's own
  docstring. Fix: `agents/common/a2a_server.py`'s `DiagnosticAgentExecutor.execute()`
  enqueues a `Task(id=..., context_id=..., status=TaskStatus(state=TASK_STATE_SUBMITTED))`
  first, then uses `TaskUpdater` for subsequent transitions.
- **`a2a-sdk` uses protobuf types, not the `a2a.types` Pydantic-style classes some
  docs reference:** `Part`, `Task`, `TaskState`, `TaskStatus` all live at
  `a2a.types.a2a_pb2`, not `a2a.types` directly (`from a2a.types import TextPart`
  fails — no such symbol in this version). `TaskUpdater.new_agent_message()` is
  the correct helper for building a response `Message`.
- **`agents/common/finding.py`'s confidence regex was too strict:** the model
  sometimes wraps the `CONFIDENCE:` marker in markdown bold
  (`**CONFIDENCE:** 0.68`), which the Phase 4 regex didn't match, leaving a
  stray "CONFIDENCE" fragment in `interpretation` and silently falling back to
  the default 0.3 confidence. Caught by `test_agents_integration.py`'s
  `"CONFIDENCE" not in finding["interpretation"]` assertion failing during Phase
  5's full regression run. Fixed with a more tolerant regex; regression test
  added (`test_build_finding_parses_markdown_bold_confidence_line`).
- **Groq + GPT-OSS + ADK/LiteLLM multi-turn tool-calling bug (worked around):**
  see Phase 2.5 above — `LiteLlm(..., include_reasoning=False)` required on every
  Groq-backed agent, A2A-served or not. `litellm.drop_params = True` does NOT fix
  it. Full detail: `orchestrator/spike/SPIKE_RESULT.md`.
- **`installing a2a-sdk pulls a newer `opentelemetry-api` than `google-adk`
  allows:** `google-adk==2.9.1` requires `opentelemetry-api<=1.42.1`; `a2a-sdk`
  installs `1.44.0`. Fix: explicitly `pip install opentelemetry-api==1.42.1`
  after `a2a-sdk`. `pip show` afterward warns that `google-api-core` wants the
  newer version back — this is a benign, non-blocking resolver warning (verified:
  `RemoteA2aAgent`/`to_a2a` import and run correctly with `1.42.1` pinned).
  Applied in both `.venv-agents/` and `.venv-orchestrator/`.
- **`google.adk.tools.mcp_tool.mcp_toolset.MCPToolset` is deprecated:** use
  `McpToolset` instead. Importing it requires the `mcp` package in the same venv
  as `google-adk` — `.venv-orchestrator/` doesn't have it (doesn't need it: only
  `McpToolset` needs `mcp`, `RemoteA2aAgent`/`to_a2a` don't).
- **MCP SDK 2.x rejects bare `dict` for structured tool output** and **renamed
  `FastMCP` to `MCPServer`** — see Phase 3 above, unchanged in Phase 5.
- Cosmetic only: after real-LLM script/tests finish (exit code 0, correct
  result), Python's asyncio Proactor event loop on Windows logs a `Fatal error on
  SSL transport` / `RuntimeError: Event loop is closed` traceback during
  interpreter shutdown. Confirmed non-blocking via explicit exit-code checks
  every time, across all 6 phases so far.
- **Pinning `httpx==0.28.1` explicitly in `orchestrator/requirements.txt`
  (Phase 6) shifted `google-api-core` from `2.38.0` to `2.34.0`** on
  reinstall — both versions satisfy `a2a-sdk`'s `google-api-core>=1.26.0`
  constraint, pip's resolver just picked differently once `httpx` was pinned.
  Verified benign: reinstalled cleanly, `RemoteA2aAgent`/`ParallelAgent`/
  `InMemoryRunner` import correctly, and the full real-A2A orchestrator test
  suite (spike + incident_manager + investigation_logic + investigation_e2e,
  8 tests) passed afterward.

## Important Decisions
- Tech stack: Python 3.11 + FastAPI + asyncio for backend/production; **Google
  ADK (Python)** for orchestrator/agents; **official `mcp` Python SDK (2.x)** for
  `mcp/`; **official `a2a-sdk` (1.x)** for A2A. Dashboard: React, deferred.
- Runtime LLM: Groq-hosted `openai/gpt-oss-120b` via ADK's `LiteLlm` wrapper with
  **`include_reasoning=False` mandatory**. Anthropic/Gemini/OpenAI-hosted must not
  be used as the NEXUS runtime provider.
- **A2A topology: separate OS processes, not in-process ADK sub-agents.** Each
  diagnostic agent is its own `uvicorn` process (own port); the Incident Manager
  is a separate process/venv (`.venv-orchestrator/`) holding only `RemoteA2aAgent`
  client proxies — never importing a diagnostic agent's module. This was an
  explicit choice per root CLAUDE.md section 10 ("prefer the independently
  addressable service/process design because it is easier to demonstrate"),
  verified concretely (`netstat`-confirmed distinct PIDs/ports, real HTTP
  request/response with real task/context IDs in `event.custom_metadata`).
- The A2A response body IS the same Finding JSON schema from Phase 4 — server-side,
  `DiagnosticAgentExecutor` reuses `DiagnosticAgent.investigate()` unchanged, so
  the evidence-first guarantees (Python-built `observation`, real MCP evidence,
  bounded/allowlisted access) carry through the A2A boundary unweakened. The A2A
  layer only changes *how* `investigate()` gets triggered (real network request
  instead of a local function call) and *how* its result gets back to the caller
  (real A2A task completion instead of a return value).
- `run_diagnostic` (cross-cutting MCP tool) remains unassigned to any of the 4
  diagnostic agents — still reserved for a future Evidence Agent/Incident
  Manager use, per the Phase 4 decision, unchanged in Phase 5.
- Dependency isolation is now a 4-times-repeated enforced pattern:
  `.venv-orchestrator/`, `.venv-mcp/`, `.venv-agents/` all separate from the
  shared backend/production venv and from each other, each with its own
  `requirements.txt` pinned to exact installed versions (updated in Phase 5 for
  `a2a-sdk`/`opentelemetry-api` in both `agents/` and `orchestrator/`).
- Sole active developer is Deepu; Mukund/Vanshika are academic-listing only — do not
  attribute implementation work to them (see root CLAUDE.md "Development Ownership").
- `production/db.py` uses in-memory SQLite (reseeds every process restart) — simplest
  option for a single-process demo service; revisit only if persistence across
  restarts is actually needed.
- **Evidence Agent and Root-Cause Critic are real, independent A2A services**
  (ports 8105/8106), not in-process reasoning called directly by
  `orchestrator/`. Same architectural choice as the 4 diagnostic agents (root
  CLAUDE.md section 10) and enforced the same way: `orchestrator/investigation.py`
  never imports `agents/evidence/agent.py` or `agents/critic/agent.py` —
  only `orchestrator/remote_call.py`'s `RemoteA2aAgent` proxy reaches them.
- **The Evidence/Critic structural-enforcement pattern extends Phase 4's
  observation/interpretation split:** `agents/evidence/agent.py`'s
  `build_hypotheses()` and `agents/critic/agent.py`'s `build_critique()` are
  the only code allowed to assign a `hypothesis_id`/trust a `verdict` — same
  principle as `agents/common/finding.py`'s `build_finding()` being the only
  code allowed to build `observation`. This is what makes "the LLM cannot
  invent raw evidence" (Phase 6 requirement) a structural guarantee rather
  than a prompt-only one.
- **`mcp/audit.py` is not read directly by the Phase 6 event bridge** — it's
  a local, in-process deque inside each diagnostic agent's own OS process,
  reached over stdio, with no network-queryable API (by design, unchanged
  since Phase 3). `orchestrator/event_bridge.py` instead emits
  `MCP_TOOL_CALL`/`MCP_TOOL_RESULT` events from the real evidence already
  present in each Finding's `evidence` list — the same real tool/arguments/
  result facts `mcp/audit.py` records privately, carried to the backend
  through data that already flows through the system. Documented explicitly
  as the actual mechanism (see `orchestrator/event_bridge.py`'s docstring),
  not left implicit.
- **`MAX_REEVALUATION_LOOPS` (env var, default 3) is the only new budget
  control implemented in Phase 6** — the fuller token/call budget system
  (`MAX_TOKENS_PER_AGENT`, `MAX_LLM_CALLS_PER_INCIDENT`,
  `MAX_TOTAL_TOKENS_PER_INCIDENT`) from root CLAUDE.md section 8 was not
  required by the Phase 6 task scope and was explicitly deferred (see "Next").

## Tests
```bash
# Phase 1/2 (backend + production), shared venv:
pip install -r requirements-dev.txt
pytest

# Phase 2.5 spike (orchestrator), isolated venv, real Groq API call:
python -m venv .venv-orchestrator
.venv-orchestrator/Scripts/python -m pip install -r orchestrator/requirements.txt
.venv-orchestrator/Scripts/python -m pytest orchestrator/tests/test_adk_groq_spike.py -q

# Phase 3 (mcp), isolated venv, requires production/ reachable:
python -m venv .venv-mcp
.venv-mcp/Scripts/python -m pip install -r mcp/requirements.txt
docker compose up -d production   # or: uvicorn service:app --port 8001 from production/
.venv-mcp/Scripts/python -m pytest mcp/tests -q

# Phase 4 (agents, direct path), isolated venv, requires production/ reachable:
python -m venv .venv-agents
.venv-agents/Scripts/python -m pip install -r agents/requirements.txt
.venv-agents/Scripts/python -m pytest agents/tests/test_finding.py agents/tests/test_agents_integration.py -q

# Phase 5 (A2A + orchestration): start all 4 diagnostic agent services first
.venv-agents/Scripts/python agents/metrics/a2a_service.py &
.venv-agents/Scripts/python agents/logs_traces/a2a_service.py &
.venv-agents/Scripts/python agents/change_analysis/a2a_service.py &
.venv-agents/Scripts/python agents/database/a2a_service.py &
.venv-agents/Scripts/python -m pytest agents/tests/test_a2a.py -q
.venv-orchestrator/Scripts/python -m pytest orchestrator/tests/test_incident_manager.py -q

# Phase 6 (Evidence Agent + Critic + re-evaluation loop): ALSO start these 2
.venv-agents/Scripts/python agents/evidence/a2a_service.py &
.venv-agents/Scripts/python agents/critic/a2a_service.py &
.venv-agents/Scripts/python -m pytest agents/tests/test_evidence_critic.py -q   # fast, no network
.venv/Scripts/python -m pytest tests/test_incidents.py -q                       # fast, no network
.venv-orchestrator/Scripts/python -m pytest orchestrator/tests/test_investigation_logic.py -q  # fast, no network
.venv-orchestrator/Scripts/python -m pytest orchestrator/tests/test_investigation_e2e.py -q    # real, needs backend/ + all 6 A2A services + production/
```
Last full run (2026-09-18, Phase 6): Phase 1/2 suite **14 passed** (8 original +
6 new incident-store tests; verified against both plain `uvicorn` and rebuilt
Docker containers, including a live `POST /incidents` smoke test through
Docker). MCP suite **22 passed** (unchanged). Agents suite (`agents/tests` —
unit + Phase 4 integration + Phase 5 A2A + Phase 6 evidence/critic unit)
**32 passed** after fixing `test_a2a.py`'s parametrize scoping (see Known
Issues) — the one prior failure (2/34 on the first run, both the same root
cause) confirmed fixed by an isolated re-run of just that test
(`test_agent_card_is_accessible`, 4 passed) before accepting the full-suite
32/32 result rather than re-spending Groq quota on a third full real-LLM pass.
Orchestrator suite (`orchestrator/tests` — spike + incident manager +
investigation logic + investigation e2e) **8 passed** (1 + 2 + 4 + 1).

## Recent Files (Phase 6)
- agents/common/reasoning_agent.py (new), agents/common/ports.py (+2 ports)
- agents/evidence/agent.py, agents/evidence/a2a_service.py, agents/evidence/__init__.py (new)
- agents/critic/agent.py, agents/critic/a2a_service.py, agents/critic/__init__.py (new)
- agents/tests/test_evidence_critic.py (new)
- agents/tests/test_a2a.py (parametrize scoping fix, see Known Issues)
- backend/app/incident_store.py (new), backend/app/main.py (5 new endpoints)
- tests/test_incidents.py (new)
- orchestrator/event_bridge.py (new), orchestrator/remote_call.py (new),
  orchestrator/investigation.py (new)
- orchestrator/tests/test_investigation_logic.py (new),
  orchestrator/tests/test_investigation_e2e.py (new)
- orchestrator/requirements.txt (+httpx==0.28.1)
- docs/API_CONTRACT.md, docs/EVENT_SCHEMA.md, agents/CLAUDE.md,
  orchestrator/CLAUDE.md, backend/CLAUDE.md

## Recent Files (Phase 5, for reference)
- agents/common/ports.py, agents/common/a2a_server.py, agents/common/remote_agent.py
- agents/common/diagnostic_agent.py (build_adk_agent made public, description +
  default_question params added, litellm.num_retries=5 set)
- agents/common/finding.py (confidence regex fixed for markdown emphasis)
- agents/metrics/a2a_service.py, agents/logs_traces/a2a_service.py,
  agents/change_analysis/a2a_service.py, agents/database/a2a_service.py
- agents/*/agent.py (x4) — description + default_question wired into DiagnosticAgent
- orchestrator/incident_manager.py (new)
- agents/tests/test_a2a.py (new), orchestrator/tests/test_incident_manager.py (new)
- agents/tests/test_finding.py (+1 regression test)
- agents/requirements.txt, orchestrator/requirements.txt (a2a-sdk, opentelemetry-api added)
- docs/ARCHITECTURE.md, docs/API_CONTRACT.md, agents/CLAUDE.md, orchestrator/CLAUDE.md

## Verification Commands
```bash
# Phase 1/2 regression:
pytest
docker compose up -d --build
curl http://localhost:8000/health
curl http://localhost:8001/health
docker compose down

# Phase 3 MCP regression:
.venv-mcp/Scripts/python -m pytest mcp/tests -q

# Phase 4 agents (direct):
.venv-agents/Scripts/python -m pytest agents/tests/test_finding.py agents/tests/test_agents_integration.py -q

# Phase 5 A2A + orchestration (4 diagnostic agent services + production must be running):
.venv-agents/Scripts/python -m pytest agents/tests/test_a2a.py -q
.venv-orchestrator/Scripts/python -m pytest orchestrator/tests/test_incident_manager.py -q

# Phase 6 (add evidence + critic services, and backend, to the above):
.venv-agents/Scripts/python -m pytest agents/tests/test_evidence_critic.py -q
.venv/Scripts/python -m pytest tests/test_incidents.py -q
.venv-orchestrator/Scripts/python -m pytest orchestrator/tests/test_investigation_logic.py -q
.venv-orchestrator/Scripts/python -m pytest orchestrator/tests/test_investigation_e2e.py -q
```
Verified 2026-09-18 (Phase 6): full regression sweep run in this order —
Phase 1/2 `pytest` 14/14 (8 original + 6 new incident-store tests; plain
uvicorn, then rebuilt Docker with a live `POST /incidents` smoke test through
the container); MCP suite 22/22 (unchanged); Agents suite 34 total tests run
in one pass (32 passed, 2 failed — both the same `test_a2a.py` parametrize-
scoping bug, see Known Issues — fixed, then verified in isolation: the 4
`test_agent_card_is_accessible` cases all pass); Orchestrator suite 8/8 (spike
1, incident_manager 2, investigation_logic 4, investigation_e2e 1). All 6 A2A
services (4 diagnostic + evidence + critic) confirmed as separate OS processes
via `netstat` (6 distinct PIDs on 6 distinct ports) before every A2A test run.
Docker containers torn down with `docker compose down` after verification; all
manually-started dev processes (production uvicorn via Docker, 6 A2A services)
killed after final verification.

## Handoff verification (post-Phase-6 cleanup pass)
Performed after Phase 6:
- Removed all `__pycache__/` and `.pytest_cache/` directories from the repo
  tree (already gitignored; removed for a clean checkout).
- Confirmed no dev servers or containers left running: `netstat` checks on
  ports 8000/8001/8101-8106 all empty; `docker compose ps` empty.
- `git status`: everything still untracked (`??`) — no commits exist yet in
  this repo (consistent with every prior phase; this session did not commit,
  per instruction to report file changes, not to commit them). `.env` and all
  4 `.venv*/` directories correctly show as ignored, never tracked.
- Secret scan: only matches for the `gsk_` pattern anywhere in the repo
  (excluding venvs and `.env` itself) are the literal placeholder
  `GROQ_API_KEY=gsk_...` in the root `CLAUDE.md`, this file's own note about
  that placeholder, and `orchestrator/tests/test_investigation_e2e.py`'s
  assertion that the literal substring `"gsk_"` never appears in persisted
  incident state — not a real key anywhere. No other secret material found.

## Blockers
None. Stopped after Phase 6 per root CLAUDE.md's phase discipline — awaiting
go-ahead for Phase 7 (dashboard) or Phase 8 (recovery/guardrails).
