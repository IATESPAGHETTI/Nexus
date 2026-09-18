# NEXUS API Contract

## Backend HTTP API (Phase 1 slice — will grow)

`backend/` exposes the persistence + control API. Dashboard and orchestrator are clients.

### `GET /health`

Liveness check for the NEXUS backend itself.

```json
{ "status": "ok", "service": "nexus-backend" }
```

### Incident state + event store — implemented (Phase 6)

Real, in-memory (per-process, resets on restart) persistence — `backend/app/incident_store.py`.
Called for real by `orchestrator/event_bridge.py` during a live investigation, not just by tests.

```text
POST /incidents                 {"description": str} -> full initial incident state
GET  /incidents/{id}            full incident state (404 if unknown)
POST /incidents/{id}/state      partial field merge (any subset of the incident-state
                                 fields below) -> full updated incident state (404 if unknown)
POST /incidents/{id}/events     {"event_type", "source", "target"?, "status"?, "payload"?}
                                 -> the created event (see docs/EVENT_SCHEMA.md envelope),
                                 also appended to the incident's timeline (404 if unknown)
GET  /incidents/{id}/events     {"events": [...]} in emission order (404 if unknown)
```

Incident state shape (root CLAUDE.md section 15):

```json
{
  "incident_id": "INC-d81b1a61",
  "description": "...",
  "status": "INVESTIGATING | DIAGNOSED | ABSTAINED",
  "created_at": "...", "updated_at": "...",
  "timeline": [{"event_id", "timestamp", "event_type", "source", "target"}],
  "evidence": {}, "agent_findings": {"<agent_name>": {"...Finding..."}},
  "agent_messages": {"<agent_name>": {"task_id", "context_id"}},
  "hypotheses": [{"...Hypothesis..."}],
  "critic_results": [{"...Critique..."}],
  "experiments": [], "recovery_plan": null, "approval_state": null,
  "action_history": [], "token_usage": {},
  "decision": {"outcome": "DIAGNOSED | ABSTAINED", "reason": "...", "loops_used": 1, "max_loops": 3}
}
```

`POST /incidents/{id}/approve` (human recovery approval) remains planned, Phase 8.

## Production (simulated) HTTP API — `production/`, separate service, port 8001

Real observability data from real requests against a seeded in-memory SQLite DB.
See `production/CLAUDE.md` for ownership. Every request also gets an `X-Trace-Id`
response header.

```text
GET  /                     {"status": "ok", "service": "nexus-production"}
GET  /health                same shape as /
GET  /metrics               {"request_count", "error_count", "by_endpoint": {...}}
GET  /logs?limit=N          {"entries": [{timestamp, level, trace_id, method, path,
                              status_code, duration_ms}, ...]}
GET  /traces?limit=N        {"traces": [{trace_id, timestamp, method, path,
                              status_code, duration_ms}, ...]}
GET  /traces/{trace_id}     single trace object (404 if unknown)
GET  /changes?limit=N       {"changes": [{change_id, type, version, deployed_at,
                              description, author}, ...]}, newest first
GET  /db/diagnostics        {"engine", "table_row_counts", "orders_by_status",
                              "recent_queries", "query_summary"}
GET  /orders                {"orders": [{id, customer, amount, status, created_at}]}
GET  /orders/{id}           single order (404 if unknown)
```

## MCP diagnostic tools — `mcp/`, real MCP server (stdio transport)

Implemented and tested (Phase 3). See `mcp/CLAUDE.md` for ownership. All 7 tools
return `{"ok": bool, ...}` and never raise to the caller.

```text
get_metrics()
  -> {"ok", "request_count", "error_count", "by_endpoint"}          [wraps GET /metrics]

query_logs(level: "INFO"|"ERROR"|None = None, limit: int = 50)
  -> {"ok", "entries", "count"}                                     [wraps GET /logs, client-side level filter]

get_trace(trace_id: str|None = None, limit: int = 20)
  -> {"ok", "trace"} if trace_id given, else {"ok", "traces"}        [wraps GET /traces[/{id}]]

get_recent_deployments(limit: int = 20)
  -> {"ok", "changes"}                                               [wraps GET /changes]

get_git_diff(paths: list[str]|None = None, max_commits: int = 5)
  -> {"ok", "paths", "commit_history_available", "commit_log_diff",
      "commit_log_truncated", "uncommitted_changes_stat",
      "staged_changes_stat"}
     paths restricted to {"production", "backend", "mcp", "docs"} — real `git log -p`
     / `git diff` on the NEXUS repo itself, not the production HTTP API.

get_database_stats()
  -> {"ok", "engine", "table_row_counts", "orders_by_status",
      "recent_queries", "query_summary"}                             [wraps GET /db/diagnostics]

run_diagnostic(name: "connectivity_check"|"error_rate_check"|"order_status_check")
  -> {"ok", "diagnostic", ...fields depend on name}
     name is validated against a fixed allowlist — never arbitrary code/SQL/shell.
```

These are the endpoints Phase 3's MCP tools wrap (metrics tool -> `/metrics`,
logs/traces tool -> `/logs` + `/traces`, change-analysis tool -> `/changes`, database
tool -> `/db/diagnostics`). `get_git_diff` is the one exception — its evidence
source is this repo's own git history, not a production HTTP endpoint (see
`mcp/git_diff_tool.py`).

Planned (not yet implemented — add here when built, keep this file in sync):

```text
POST /incidents/{id}/approve    human approval for a recovery plan (Phase 8)
GET  /incidents/{id}/events     currently poll-only; SSE/websocket streaming for
                                 the live dashboard is Phase 7
```

## A2A protocol — implemented (Phase 5)

Real [Agent2Agent](https://a2a-protocol.org/) protocol, `a2a-sdk==1.1.4`, via
`google.adk.a2a.utils.agent_to_a2a.to_a2a()` (server) and
`google.adk.agents.RemoteA2aAgent` (client). Not a custom JSON envelope — this
section documents the real shapes as observed, not an illustrative design.

### Topology

```text
agents/metrics/a2a_service.py          -> own process, http://127.0.0.1:8101
agents/logs_traces/a2a_service.py      -> own process, http://127.0.0.1:8102
agents/change_analysis/a2a_service.py  -> own process, http://127.0.0.1:8103
agents/database/a2a_service.py         -> own process, http://127.0.0.1:8104
agents/evidence/a2a_service.py         -> own process, http://127.0.0.1:8105 (Phase 6)
agents/critic/a2a_service.py           -> own process, http://127.0.0.1:8106 (Phase 6)
orchestrator/incident_manager.py       -> A2A client only (RemoteA2aAgent x4,
                                           diagnostic agents, Phase 5)
orchestrator/investigation.py          -> A2A client only (RemoteA2aAgent to
                                           evidence_agent + root_cause_critic
                                           via remote_call.py, Phase 6)
```

The Evidence Agent and Root-Cause Critic are served by the exact same
`agents/common/a2a_server.py` (`DiagnosticAgentExecutor`/`build_a2a_app`) as the
4 diagnostic agents — they carry no MCP tools (see `agents/common/reasoning_agent.py`),
but are otherwise indistinguishable at the protocol level: real Agent Cards,
real Task lifecycle, real JSON-RPC.

Ports: `agents/common/ports.py`. Each service is `mcp/server.py`'s diagnostic
agent (unchanged from Phase 4) wrapped by `to_a2a()`.

### Agent Card

`GET http://127.0.0.1:<port>/.well-known/agent-card.json` — auto-built by ADK's
`AgentCardBuilder` from the agent's name/description/tools. Real example
(metrics agent):

```json
{
  "name": "metrics_agent",
  "description": "NEXUS diagnostic agent: investigates request metrics (counts, error rates, p99 latency) via MCP get_metrics.",
  "supportedInterfaces": [{ "url": "http://127.0.0.1:8101", "protocolBinding": "JSONRPC", "protocolVersion": "1.0" }],
  "capabilities": { "streaming": true },
  "skills": [
    { "id": "metrics_agent", "name": "model", "description": "...", "tags": ["llm"] },
    { "id": "metrics_agent-get_metrics", "name": "get_metrics", "description": "Request counts, error counts, and latency (avg/p99) per endpoint...", "tags": ["llm", "tools"] }
  ]
}
```

### Request/response flow

1. `RemoteA2aAgent` (client, in `orchestrator/incident_manager.py` or any test)
   sends a real A2A `Message` (role `ROLE_USER`) to the target service's JSON-RPC
   endpoint.
2. The service's `DiagnosticAgentExecutor` (`agents/common/a2a_server.py`)
   receives it via a real `a2a.server.agent_execution.RequestContext`, enqueues a
   `Task` (state `TASK_STATE_SUBMITTED` -> `TASK_STATE_WORKING`), runs the SAME
   `DiagnosticAgent.investigate()` used in Phase 4 (real MCP tool calls, real
   Groq/GPT-OSS-120B reasoning), and completes the task (state
   `TASK_STATE_COMPLETED`) with an agent `Message` whose text is the JSON-encoded
   Finding (see schema below).
3. The client's ADK `Event` carries `custom_metadata` proving the protocol hop
   actually happened — real example:

```json
{
  "a2a:task_id": "8b0932b3-4e08-458a-9690-94c68a1235f3",
  "a2a:context_id": "dbdf0dde-bcf9-47db-b7fe-a0723fd5a4a1",
  "a2a:request": { "messageId": "...", "role": "ROLE_USER", "parts": [{ "text": "Summarize current request metrics." }] },
  "a2a:response": { "id": "8b0932b3-...", "status": { "state": "TASK_STATE_COMPLETED", "message": { "role": "ROLE_AGENT", "parts": [{ "text": "{\"finding_id\": \"find-f446f278\", ...}" }] } } }
}
```

### Parallel dispatch (Incident Manager)

`orchestrator/incident_manager.investigate_incident(text, agent_names=None)`
builds an ADK `ParallelAgent` whose `sub_agents` are `RemoteA2aAgent` proxies for
each named diagnostic agent (all 4 by default) and runs it once — ADK's
`ParallelAgent` invokes all sub-agents concurrently, so all 4 real A2A requests
are in flight at once, each with its own `task_id`/`context_id`. Returns
`{"findings": {agent_name: Finding}, "a2a": {agent_name: {task_id, context_id}}, "agents_dispatched": [...], "agents_responded": [...]}`.

### Known constraint: Groq free-tier TPM rate limit

Groq's `openai/gpt-oss-120b` free tier is limited to 8000 tokens/min, shared
across all 4 agents. A 4-way parallel burst can trip a real `RateLimitError`.
`agents/common/diagnostic_agent.py` sets `litellm.num_retries = 5` so transient
429s are retried with backoff rather than failing the dispatch — see
`docs/PROJECT_STATE.md` "Known Issues" for the observed failure/fix.

## Agent finding schema — implemented (Phase 4), `agents/common/finding.py`

Every diagnostic agent (`agents/metrics`, `agents/logs_traces`, `agents/change_analysis`,
`agents/database`) returns findings shaped like (real example, not illustrative):

```json
{
  "finding_id": "find-28fc189c",
  "agent": "database_agent",
  "observation": "get_database_stats({}) -> ok=True, fields=['engine', 'table_row_counts', 'orders_by_status', 'recent_queries', 'query_summary']",
  "source": "database_agent",
  "window": { "start": "2026-09-18T09:37:18Z", "end": "2026-09-18T09:37:26Z" },
  "evidence": [
    {
      "evidence_id": "ev-75f02cbd",
      "tool": "get_database_stats",
      "arguments": {},
      "result": { "ok": true, "table_row_counts": { "orders": 10 }, "...": "..." },
      "timestamp": "2026-09-18T09:37:26Z"
    }
  ],
  "interpretation": "The database contains a single orders table with only 10 rows...",
  "confidence": 0.97,
  "limitations": "none noted"
}
```

`finding_id` and each `evidence[].evidence_id` are unique per call. `observation`
is built **in Python**, purely from the raw MCP tool result(s) — never from the
model — so a guess can never be silently recorded as a fact; `interpretation` is
the model's own text (with a trailing `CONFIDENCE: <0-1>` line stripped out into
the `confidence` field). If the model didn't report a parseable confidence, a
conservative default (0.3) is used and noted in `limitations`.

## Hypothesis schema — implemented (Phase 6), `agents/evidence/agent.py`

Produced by the Evidence Agent's `build_hypotheses()` from the diagnostic
agents' real Findings (real example, not illustrative):

```json
{
  "hypothesis_id": "H1",
  "statement": "The database is the primary bottleneck for checkout latency.",
  "supporting_evidence_ids": ["ev-75f02cbd"],
  "contradicting_evidence_ids": [],
  "confidence": 0.8,
  "missing_evidence": ["trace correlation for request X"],
  "requested_next_investigation": "logs_traces_agent: pull traces for window W",
  "status": "PROPOSED",
  "revision": 1,
  "created_at": "2026-09-18T09:37:26Z",
  "dropped_invented_evidence_ids": 0
}
```

`status` in `{PROPOSED, UNDER_REVIEW, CHALLENGED, NEEDS_EVIDENCE, SUPPORTED, REJECTED, ABSTAINED}`
— transitioned only by `orchestrator/investigation.py`'s re-evaluation loop,
never by the Evidence Agent itself (which only ever proposes at `PROPOSED`).
`hypothesis_id` is always assigned in Python (`H1`, `H2`, ... by descending
confidence), never trusted from the model. `supporting_evidence_ids`/
`contradicting_evidence_ids` are filtered to ids that actually exist in the
input Findings — an invented id is dropped and counted in
`dropped_invented_evidence_ids`, never recorded as fact.

## Critique schema — implemented (Phase 6), `agents/critic/agent.py`

Produced by the Root-Cause Critic's `build_critique()` for a single hypothesis
under review (real example):

```json
{
  "critique_id": "crit-3fa1c9d2",
  "hypothesis_id": "H1",
  "verdict": "SUPPORTED",
  "contradictions": [],
  "unsupported_assumptions": [],
  "alternative_explanations": ["A slow downstream payment API could also explain the latency."],
  "requested_evidence": [],
  "rationale": "The database diagnostics show elevated query times consistent with the hypothesis, and no evidence in the pool contradicts it.",
  "evidence_pool_size": 3,
  "timestamp": "2026-09-18T09:41:02Z"
}
```

`verdict` in `{SUPPORTED, CONTRADICTED, INSUFFICIENT_EVIDENCE, REQUEST_MORE_EVIDENCE, ABSTAIN}`.
An unparseable or out-of-enum verdict from the model is never trusted at face
value — `build_critique()` normalizes it to `INSUFFICIENT_EVIDENCE`, which
keeps `orchestrator/investigation.py`'s loop asking for more evidence rather
than silently treating a garbled reply as support or contradiction.

## Re-evaluation loop — implemented (Phase 6), `orchestrator/investigation.py`

`run_investigation(incident_description, agent_names=None, max_loops=None) -> dict`
returns the final persisted incident state (fetched back from `backend/`, not
an in-memory copy). Bounded by `MAX_REEVALUATION_LOOPS` (env var, default 3;
root CLAUDE.md section 8/14) — the loop can only ever end in `DIAGNOSED` or
`ABSTAINED`, never left hanging or forced to a diagnosis. See
`orchestrator/CLAUDE.md` for the exact per-verdict transitions and
`docs/EVENT_SCHEMA.md` for every event type this loop emits.
