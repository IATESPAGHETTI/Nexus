# NEXUS Project State

## Presentation: Architecture section (2026-10-01) — implemented; `tsc -b` clean; checked in browser at desktop + 375px
Dashboard-only. New `components/story/ArchitectureSection.tsx` + `Architecture.module.css`, inserted
between the agent bento and the steps rail on `/presentation`; "Architecture" added to `PillarsNav`.
Contents: an SVG hub-and-spoke diagram (Incident Manager, 4 specialists fan-out, Evidence/Critic/Recovery
sequential, guardrails, event store; ports 8101-8107), six communication-pattern cards, six design principles.
- **Honesty**: only hierarchy/hub-and-spoke, parallel fan-out/gather, pipeline+feedback loop and the event
  log are marked "Implemented". Peer-to-peer mesh and agent-to-agent broadcast/pub-sub are marked "Not used,
  by design" — NEXUS agents never call each other; all calls go through the Incident Manager, and the dashboard
  polls the event store (no push stream). The "why not" text is design rationale, not a measured comparison.
- The diagram is labelled as architecture drawn from code, not a recorded run. Static content, no backend data.
- Not verified: animation feel (pane was hidden, so fade-ins were mid-transition in screenshots).

## Recovery fixes + cost guard (2026-09-21/22) — implemented; deterministic tests pass; NOT verified against a live LLM (provider key was revoked mid-session)
- **Found (from `backend/.demo_logs/`)**: (1) a run was approved and marked **RESOLVED** while
  production still had `db_slowdown: true` — `orchestrator/recovery.py::_verify_recovery` only
  checked the metrics error RATE, and a latency-only fault has zero errors, so it always passed.
  (2) 3 of 4 diagnosed runs ended approval `EXPIRED` (window was 120s; once it closes the
  orchestrator has exited, so a late Approve does nothing). (3) Every plan chose
  `restart_service`, which does not clear `db_slowdown` (only `scale_resources` does).
  (4) The plan sat at the bottom of a long card.
- **Fixes**: verification now decided by a deterministic live probe (`_probe_service`: 5 timed
  real GETs each to `/orders` and `/orders/1`, median < `VERIFICATION_LATENCY_MS` (100) and
  failures < 20%); the Metrics Agent re-check is supporting evidence only and fail-soft. New
  `orchestrator/tests/test_verification.py` (6 tests, incl. the exact false-RESOLVED case).
  `MAX_APPROVAL_WAIT_SECONDS` default 120 -> 600 (`guardrails/config.py`). Recovery Agent
  `ACTION_CATALOG`/instruction now state which symptom each action remedies (slow DB queries ->
  `scale_resources`, restart does NOT fix them). Dashboard: approval banner at the TOP of the
  Command Center (Approve / Keep investigating), clear "window closed, nothing executed" state,
  and the real post-fix probe numbers shown for RECOVERED / NOT VERIFIED.
- **Cost guard (UI)**: "Inject Database Slowdown" now asks for confirmation (states it makes
  ~10-30 paid model requests) and is disabled while an investigation is in progress or awaiting
  approval. NEXUS has no per-call token accounting yet (UsagePanel is "Unavailable from
  provider"), so dollar cost cannot be computed here — use the provider's usage page.
- **Cost finding**: idle NEXUS makes zero model calls (agent services logged only agent-card
  GETs plus A2A POSTs for real runs). Five investigations were launched by the button after the
  key was fixed (23:09, 23:11, 23:12, 23:13, 23:44 IST); the 23:44 run used 3 re-evaluation
  rounds (18 agent tasks). Only two were started by the assistant.
- **Housekeeping**: `.gitignore` now also ignores `reference_web/`, `.env.*` (keeps
  `.env.example`). Verified `.env` was never committed and no key-like strings exist in the tree
  or git history. 76 orphaned MCP server processes (leaked per investigation round) were killed;
  the leak itself is NOT fixed. The 7 agent services were left STOPPED on purpose (key rejected
  by DeepSeek, and to avoid surprise spend); restart them only after a new key is set in `.env`.
- Tests: agents 27, guardrails+orchestrator logic 33 (incl. 6 new), backend 10 — all pass.

## UI redesign after the reference site (2026-09-21) — implemented; visually checked; user has NOT yet accepted it
Whole-dashboard redesign modelled on `reference_web/` (a saved copy of a public marketing site).
A first attempt only re-coloured the old layout and was rejected as "merely colors"; this pass
rebuilt page structure and scroll animation. Only the *design language and interaction patterns*
were borrowed: no reference text, logos, images or paid fonts (PolySans / Perfectly Nineties are
NOT used; Inter + JetBrains Mono are self-hosted via `@fontsource-variable/*`).
- **Theme**: the reference is a *light* page with dark product frames inside it. Marketing
  pages (`/`, `/presentation`) are now light (`--lt-*` tokens), with dark frames/bands using the
  existing `--nx-*` dark tokens (kept for the incident pages and all data panels). Brand
  vermilion; green/amber/red stay state-only.
- **New shell** (`components/layout/AppShell`): announcement strip driven by REAL backend status
  (off / connecting / unreachable / live n of 7) + minimal nav with a pill CTA; dark variant on
  incident pages.
- **New story components** (`components/story/`): pinned hero (230vh sticky, word-by-word
  blur/rise headline, perspective grid, a 16:9 product frame that GROWS on scroll while the copy
  swaps — scroll progress via motion `useScroll`, frame UI scaled from a fixed design size);
  tech marquee (names only, no logos); "The problem" marker + two-tone headline; dot-grid
  statement whose words fill on scroll; "The solution" side-by-side window panes (labelled
  illustrative, not a recorded run; content derives from the real architecture and
  `evaluation/baselines.py`); bento agent cards (mono panels list real tool/enum names, never
  results); 6-step rail; dark "live system" band containing the existing real-data pipeline +
  Command Center; closing CTA; floating pillars nav.
- **Pages**: `/presentation` = full story; `/` (Overview) = hero + marquee + live band + recent
  incidents. Removed: old `HeroSection`, `LifecycleSection`, `AgentTeamSection`, their CSS.
- **Honesty rules unchanged**: the hero frame and strip show only real state (agents OFF /
  connecting / unreachable read as such; nothing simulated).
- **Rollback**: previous UI (before any redesign) is in `dashboard/_backup_ui_v1/`. Restore by
  replacing `dashboard/src` with `_backup_ui_v1/src`. Delete the backup once the new UI is accepted.
- **Verified**: `tsc -b` + `npm run build` clean; desktop `/`, `/presentation`, incident page and
  390px checked in the browser; hero growth confirmed by sampling real scroll (frame 576→683px at
  300px scroll, copy fade/swap wired). Screenshots were unreliable after scrolling (tool quirk),
  so lower sections were captured with a tall viewport and the hero hidden.
- **Not done / caveats**: the reference's rolodex/bento product videos and its light "product
  screenshot" imagery were not recreated; animations were checked by sampling, not by eye in a
  real scrolling browser — please judge the feel yourself.

## Presentation page: professor-friendly layer (2026-09-21) — implemented; verified against real backend+production, NOT against a live LLM investigation
Dashboard-only change (`dashboard/`, one `.claude/launch.json` addition). No edits to
`backend/`, `orchestrator/`, `agents/`, `mcp/`, `guardrails/`, `production/`.
- **Route `/presentation`** (nav: Overview | Incidents | Agents | Presentation — no
  "Metrics" page exists in the codebase, so none was invented). All existing pages
  (`/`, `/incidents/:id`) kept and re-checked.
- **Narrative layer**: hero, 6-step lifecycle, hospital-team analogy for the 7 agents,
  live 7-agent pipeline, Agent Master Switch, 7-question Command Center. Technical
  Details drawer holds IDs, MCP calls, A2A task/context IDs, raw events, raw JSON.
  `lib/presentation.ts` derives all plain-English views; every string is either a fixed
  label translating a real event/verdict/action or text the real agents produced.
- **Real-vs-offline rules**: OFF = "AGENTS OFFLINE · ILLUSTRATIVE DEMO", a data-free
  explanation of the 7 questions (no incident, no numbers). ON + probe in flight =
  "CONNECTING…". ON + no backend = "BACKEND UNREACHABLE", nothing substituted. ON + backend
  = real status/events only; pipeline node states (working/reported/failed) come from real
  events. Reasoning-agent "working" is derived from ordered event counts (see docstring).
- **Fake data removed** (was present before this pass): hardcoded static scenario
  (`staticScenario.ts`), live mapper with invented agent names/MCP URIs/filler claims
  (`liveToHuman.ts`), hero telemetry (P99 2,420ms/14.2%/89%), scripted fallback on
  backend-down, inaccurate agent/lifecycle copy ("Prometheus", "replica lag",
  "continuously samples error budgets", "zero hallucinations"). `InvestigationPage` also
  stopped substituting the static scenario when the backend/incident is missing.
- **Demo scenario: `db_slowdown`** (chosen after inspecting `fault_injection/scenarios.py`
  and measuring in-process): with `/orders` traffic, real evidence = query ~260ms vs 0.03ms
  healthy, `/orders` avg ~206ms/p99 ~263ms, 0 errors, no deploy entry. Without traffic the
  fault leaves NO signal, and nothing in NEXUS generates traffic. The button therefore
  sends real `GET /orders` requests (`sendCustomerRequests`, via a narrow Vite proxy
  `/production` that allows only `GET /orders[/id]`; `/admin/*` unreachable). Incident
  description is symptom-only (does not name the cause). Fault logic untouched.
- **Recovery UI**: Approve / Keep Investigating shown only when the real incident has a
  `recovery_plan` with `approval_state.PENDING`; EXECUTING → VERIFYING → RECOVERED are
  derived from real approval state + `RECOVERY_EXECUTED`/`RECOVERY_VERIFIED`/status.
- **Also fixed**: `deriveAgentStates` sorted `evt-N` ids lexically (evt-10 before evt-2);
  now numeric.
- **Verified (2026-09-21)**: `tsc -b` + `npm run build` clean; dev server on :5173. Browser:
  OFF, ON+backend-down, ON+backend/production-up (0/7 agents), real inject flow (baseline
  requests → `POST /demo/investigate` → real incident + production state), Overview,
  incident page, missing-incident page, Technical Details, 390px layout (no overflow;
  pipeline stacks). Abstention, recovery-pending, real `POST /approve`, EXECUTING/
  VERIFYING/RECOVERED were exercised with **hand-written test incidents posted through the
  real backend endpoints (verification harness only, not product data; wiped afterward)**.
- **NOT verified**: a live LLM-driven investigation of the db_slowdown scenario through
  this UI (agent services + DeepSeek were not started). Screenshots were unreliable while
  the pane was hidden (Framer Motion does not animate then), so most checks were DOM text.
- **First real run through the UI (2026-09-21, later)**: with all 7 agent services up
  (7/7) the inject button worked end to end (real incident, real orchestrator subprocess,
  real events), but **every agent's DeepSeek call was rejected: "Authentication Fails …
  api key is invalid"** (key in `.env` has a valid shape: 35 chars, `sk-`, no quotes/space;
  no OS env var shadows it) → 4/4 diagnostic agents failed → Evidence Agent had nothing →
  honest ABSTAIN. Blocker is the key (revoked/expired/wrong), NOT the UI. Fix: replace
  `DEEPSEEK_API_KEY` in `.env`, then restart the agent services (they read `.env` at
  startup). The dashboard now explains "no agent returned evidence" and keeps polling while
  the tab is in the background. `.claude/launch.json` gained the 7 agent configs (the
  preview tool caps at 5 servers, so 5 agents were started as background processes).
- **Live run PASSED (2026-09-21, after the key was replaced and the 7 agent services
  restarted — they read `.env` only at startup)**: clicking the UI button ran the real
  chain twice: 4/4 diagnostic agents reported (real MCP evidence: `/orders` avg ~248ms,
  p99 ~266ms, 0 errors; DB queries ~256-261ms), Evidence Agent 3 hypotheses (85% top),
  Critic SUPPORTED, DIAGNOSED, Recovery Agent proposed a plan, guardrails validated,
  `HUMAN_APPROVAL_REQUESTED`. **Approval was not clicked** (so execution/verification not
  exercised live). Observation: both runs the Recovery Agent proposed `restart_service`,
  which per `production/state.py` does NOT clear `db_slowdown` (only `scale_resources`
  does) → approving would run, then honestly fail verification. Recovery logic untouched.
- **Bug fixed**: `deriveAgentStates` read `source` for `AGENT_STARTED`, but the
  orchestrator emits source=incident_manager/target=<agent>, so agents never showed
  RUNNING (also affects `InvestigationPage`). Verified: the 4 agents now show "working now"
  during a real run. Card also clamps long agent text and no longer repeats it 3x.
- **Known limitation**: `GET /demo/status` takes ~14s when no agent service is up
  (sequential probes), so ON shows "CONNECTING…" that long. Existing backend behaviour.

## Provider default change: DeepSeek (2026-09-19) — implemented + verified
- `runtime_config.py` now defaults to `deepseek/deepseek-chat` and treats
  DeepSeek as the official/production provider. Groq
  (`groq/openai/gpt-oss-120b`) and Gemini (`gemini/gemini-2.5-flash`) remain
  supported opt-ins; the `include_reasoning=False` workaround is still applied
  only when the resolved provider is Groq.
- Local `.env` now uses `DEEPSEEK_API_KEY` (renamed from a previously
  unreferenced lowercase `deepseek` variable). `.env.example` documents the
  DeepSeek default plus the Groq/Gemini overrides. No secret value was printed
  or committed.
- Provider-selection tests updated/added in `evaluation/tests/test_scoring.py`.
- Added `agents/tests/deepseek_mcp_smoke.py`: a non-mocked, one-shot real
  DeepSeek -> ADK -> LiteLLM -> MCP `get_metrics` -> structured Finding smoke
  test (run manually with `.venv-agents` while production/ is reachable).
- Deterministic regression: evaluation 16 passed; orchestrator logic+recovery
  13 passed; agents finding/evidence/critic/recovery 27 passed (56 total).
- Real DeepSeek smoke test PASSED 2026-09-19: provider=deepseek,
  model=deepseek-chat, litellm string `deepseek/deepseek-chat`, one real MCP
  `get_metrics` call returned ok=True, a real `find-...` Finding produced, and
  interpretation text present. A benign asyncio SSL teardown traceback appeared
  after the result during interpreter shutdown (exit code remained 0).
- Not done this pass: the full NEXUS investigation / 3-arm benchmark, deferred
  until this single-agent DeepSeek smoke test passed.

## Current Phase
Phase 10 (10A Full-System Integration, 10B Reproducible End-to-End Demo,
10C Documentation & Academic Packaging, 10D Final Verification & Cleanup) —
**all four subphases DONE (2026-09-18)**, with two items honestly flagged as
still pending a live Groq call rather than run/faked this session: the actual
`orchestrator/run_demo.py` investigation run, and Phase 9's official 3-arm
benchmark. Neither is blocked by missing code — both are unblocked purely by
Groq daily-quota headroom. See `NEXUS_PHASE10_PLAN.md` for full detail on
each subphase.

## Current Task
User explicitly asked to continue past Phase 7 into Phase 8 (Recovery +
Safety) then Phase 9 (Fault Injection + Evaluation), verify thoroughly, run
the actual experiments/evaluation, update this file, then stop. Phase 8 is
implemented + tested (unit-level fully; live-verified piecemeal — see below).
Phase 9's code (fault_injection/, evaluation/) is implemented + unit-tested;
the actual live benchmark run across all 5 scenarios/3 arms could not be
completed in this session because the Groq account's daily token quota (TPD
200000) was exhausted mid-session by the live verification calls this same
work needed to make — documented honestly below, not silently skipped or
faked. A cleanup pass was performed after this session's live verification
(all manually-started processes — production, backend, all 7 A2A services —
killed, kill switch sentinel file removed, scratch scripts deleted; ports
8000/8001/8101-8107 confirmed free). STOPPED per root CLAUDE.md's phase
discipline and the user's own instruction to stop here.

### Continuation check — 2026-09-18
- Read the Phase 9 fault-injection/evaluation implementation and its local
  contracts. Found and fixed one controlled-recovery consistency issue:
  `scale_resources` now clears the simulated `db_slowdown` fault as well as
  `resource_exhaustion`, matching the documented `FI-db-slowdown` recovery
  expectation. Guardrails metadata and Recovery Agent guidance now state that
  scope; `tests/test_fault_recovery.py` covers both flags.
- Local test execution was restored without reinstalling Python or recreating
  a venv. Python 3.10.11 was present at the path all four NEXUS venvs use;
  the earlier `Access is denied` result was the sandbox's process-execution
  restriction, not a missing interpreter. Each venv's `python --version` and
  `python -m pip --version` now succeeds when the existing local executable is
  run with the required permission.
- Deterministic verification after the provider-selector change: provider
  selection tests **3 passed**; evaluation suite **14 passed**; backend and
  production suite **29 passed**; fault scenario suite **5 passed**; fast
  agent suite **27 passed**; orchestrator + guardrails suite **27 passed**;
  MCP tool suite **16 passed** and MCP audit/protocol suite **6 passed**.
  The temporary local production server used for MCP testing was stopped.
- `docker compose config --quiet` passed (Docker emitted only an access warning
  for its user config file). Dashboard production build could not start:
  Node 24 is present, but the installed `npm` launcher refers to a missing
  `%APPDATA%\\npm\\node_modules\\npm\\bin\\npm-cli.js`.
- The live Phase 9 benchmark remains intentionally unstarted: no safe
  provider-side quota inspection exists without consuming a Groq request, and
  the durable handoff records exhausted TPD. Do not spend a real call until
  the runtime interpreter and confirmed quota headroom are available.
- Added an opt-in runtime-provider selector in `runtime_config.py`.
  `NEXUS_LLM_PROVIDER=groq` and `NEXUS_LLM_MODEL=openai/gpt-oss-120b` remain
  the default and only official benchmark configuration. A Gemini override
  uses the existing local `GEMINI_API_KEY` without reading or persisting it;
  its experiment reports are structurally labelled
  `development_validation_not_official_nexus_benchmark`.

### Dashboard substantial visual redesign: InvestigationCanvas (2026-09) — implemented + live-verified against a real running stack
Direct response to user pushback that the prior pass was still "too centered,
too many cards, doesn't feel live" and a request to not iterate further on
the card-stack layout. Summary:
- **New `InvestigationCanvas.tsx`/`.module.css`** replaces `AgentConstellation`
  (deleted) as the investigation page's visual centerpiece: the 4 diagnostic
  agents arranged in a cross/compass layout (Metrics top, Database bottom,
  Logs & Traces / current-hypothesis / Change Analysis in the middle row),
  connected by thin bars whose color is each agent's real `agentStatusTone()`
  — idle=hairline gray, running=amber, completed=green, failed=red — never
  decorative. The center card shows the real leading hypothesis
  (`incident.hypotheses[0]`, confidence bar, status badge) or an honest "no
  hypothesis yet" state.
- **`InvestigationPage` restructured into a real 2-column command-center
  layout** (`.body { grid-template-columns: 1fr 380px }`): main column
  (canvas -> hypotheses -> critic -> re-evaluation -> decision -> recovery)
  + a persistent right-hand live activity rail (A2A stream + MCP activity +
  usage, both now default-open, not collapsed) — matching the handoff doc's
  target structure instead of one long centered card stack.
- **A real bug caught by an actual screenshot, not assumed fixed**: the
  first implementation of `InvestigationCanvas` used absolute positioning
  ("compass point" placement via `top/left/right/bottom` percentages) and
  looked fine in isolated reasoning but broke under a real render — a
  screenshot at 1400px width showed the Database card floating disconnected
  with a large dead gap, and at ~777px it caused horizontal page overflow.
  Rewritten as a flow-based 3-row layout (CSS Grid + flexbox, no absolute
  positioning) — verified visually correct afterward at multiple widths.
  Consistent with this session's explicit instruction not to declare a
  redesign complete from a screenshot alone: the screenshot is what caught
  the bug, and the fix was verified with another real screenshot after.
- **Full real stack started and verified live, exactly per the requested
  checklist**: production (8001) + backend (8000) + all 7 A2A agent services
  (8101-8107) started for real; `GET /demo/status` and each service's real
  `.well-known/agent-card.json` confirmed 7/7 reachable; clicked the real
  "Inject Controlled Failure" button in the actual browser (not curl) and
  watched a genuine investigation run end-to-end through the new UI:
  `INCIDENT_CREATED` -> 4x real `AGENT_STARTED` -> all 4 diagnostic agents'
  real Groq/A2A calls this time failed with a real, honestly-labeled reason
  (`"no A2A response (Groq rate limit or agent unavailable)"`, `status:
  "failed"`) -> real `A2A_MESSAGE_SENT` to the Evidence Agent (which
  correctly had nothing to work with) -> real `ABSTENTION` ("no open
  hypothesis left to evaluate") -> `INCIDENT_STATUS_CHANGED` to `ABSTAINED`.
  The dashboard's `InvestigationCanvas` correctly rendered all 4 agents as
  `FAILED` (red), the center card's honest empty state, and `DecisionPanel`
  correctly rendered the abstention — all from real polling, confirmed via
  direct network-request inspection (`/api/incidents/.../events` returning
  the real growing event list), not asserted from a single glance.
  **Honest disclosure, again**: this means a second real burst of Groq
  calls was made this session (this time at the user's own explicit
  request/checklist, not an accident like the previous one) — quota clearly
  has *some* headroom (all 4 calls were dispatched) but not enough to avoid
  rate-limiting a 4-way parallel burst, consistent with the known Groq
  free-tier TPM limit documented since Phase 4/5.
- Verified: `npm run build` clean; root pytest 29/29; orchestrator
  fast-logic + guardrails 27/27. All test processes (production, backend, 7
  agent services + their MCP stdio children) left running at the end of
  this pass per explicit user request to keep exploring live — not torn
  down this time (unlike prior passes).

### Dashboard follow-up pass: startup performance + professor mode (2026-09)
Response to `NEXUS_UI_LIVE_COMMAND_CENTER.md` handoff doc's Priority 1 and
section 18. Summary:
- **Startup performance investigated (Priority 1), not blindly "fixed"**:
  confirmed via real network-request capture that `npm run dev`'s ~100+
  separate unbundled module requests per full page load is inherent Vite
  dev-server behavior (fast HMR, not a bug), not a code defect — a suspected
  runaway `/api/demo/status` polling loop turned out to be stale requests
  from this session's own rapid file-edit/HMR-reload cycle, not a live
  issue (confirmed: zero new requests over a clean 6s window against the
  5s poll interval). The real fix: `npm run build && npm run preview`
  serves the bundled production build — confirmed via a real preview-server
  load: 4 requests total (`index.html`, one JS bundle, one CSS bundle, one
  `/api/demo/status` call) vs. dev mode's 100+, with system-status rows
  resolving independently, not blocking the shell — exactly the "no global
  spinner" behavior already architected into `MissionControlPage`.
  `vite.config.ts` gained a `preview.proxy` block (was missing — `npm run
  preview` couldn't reach `backend/` at all without it) so this is now a
  real, working option for demo day, not just a dev-server convenience.
- **"Professor mode" one-sentence descriptions (section 18)**: added as
  native `title` tooltips (no tutorial overlay) — the 4 agent cards, A2A
  panel, MCP panel, Root-Cause Critic panel, and Recovery panel headers.
- **Fabrication audit**: grepped the entire dashboard source for
  `Math.random`/`setTimeout`/`setInterval`/mock-event patterns/hardcoded
  incident IDs — none found.
- **Deferred, explicitly, not silently**: the fuller spatial "agent
  constellation with connector paths to a central hypothesis" (handoff doc
  section 10) and "A2A as message bubbles, not a row table" (section 12)
  redesigns were not attempted this pass — real, larger UI work with
  meaningful layout-correctness risk, out of reach of this pass's time
  budget. The existing `AgentConstellation` (responsive card grid) and
  `A2AStreamPanel`/`MCPActivityPanel` (sender→recipient / agent·tool rows
  with real result values, e.g. `{"error_rate":0.35}`) already satisfy the
  "real data, not a generic log" requirement, just not the full spatial/
  conversational visual treatment described.
- Verified: `npm run build` clean; root pytest (29/29) and orchestrator
  fast-logic + guardrails suites (27/27) clean.

### Dashboard product-direction change: live command center (2026-09) — implemented + verified
User-directed reversal of the prior colorful-glass visual pass and a real
product-concept change: from "dashboard showing an investigation" to "live
command center for an autonomous investigation." Full detail in
`dashboard/CLAUDE.md`/`backend/CLAUDE.md`. Summary:
- **Background removed**: the ambient blurred sage/blue/peach color fields
  (previous session's pass) were removed entirely — user feedback was that
  they read as a lifestyle-app aesthetic, wrong for NEXUS. Replaced with a
  restrained neutral palette (warm off-white/stone, no color) and two faint
  static (unanimated) tonal gradients, no blur filter.
- **New Mission Control home page** (`MissionControlPage.tsx`, replaces
  `IncidentListPage.tsx`): real system status (production/agent
  reachability, live-probed, never hardcoded) plus one real primary action.
- **The "Inject Controlled Failure" button is a real action, not a demo
  simulation** — new backend endpoints (`backend/app/demo.py`,
  `POST /demo/investigate` + `GET /demo/status`): real fault injection via
  production's existing `/admin/fault/inject`, a real incident via
  `incident_store`, and — only if A2A agent services are actually
  reachable — a real `orchestrator/investigation.py` `run_investigation()`
  launched as a detached subprocess. `run_investigation()` gained an
  additive `incident_id: str | None` param (default `None` preserves all
  existing behavior/tests) so it can attach to an incident the dashboard
  already created instead of always creating its own;
  `orchestrator/run_demo.py` gained a matching `--incident-id` flag.
- **New wide "command center" layout**: persistent left sidebar
  (`components/layout/Sidebar.tsx`/`AppShell.tsx` — Mission Control / Active
  Incidents / Recent Incidents, all real localStorage-cached + live-refetched
  data / System Status) + a full-width investigation page (was a
  900px-centered column, now 1440px).
- **Recovery approval is now a real, wired action**: `RecoveryPanel` gained
  live Approve/Reject buttons that call the real, pre-existing
  `POST /incidents/{id}/approve`. Fixed a real staleness bug while wiring
  this: `useIncidentQuery` stopped polling once an incident left
  `INVESTIGATING`, but the entire real recovery flow (propose -> validate ->
  approve -> execute -> verify) happens while status stays `DIAGNOSED` — so
  the panel would never have shown the result of clicking Approve without
  a manual refresh. Now polls through both `INVESTIGATING` and `DIAGNOSED`,
  stopping only on the genuinely terminal `ABSTAINED`/`RESOLVED`.
- **Live-verified end-to-end, for real, in this session**: started
  production + backend + all 7 A2A services, called `POST /demo/investigate`
  with all 7 agents reachable, and confirmed `investigation_triggered: true`
  with real `AGENT_STARTED` events for all 4 diagnostic agents landing in
  the real backend event store within seconds — the full button-click ->
  fault-injection -> incident-creation -> subprocess-launch -> real-A2A-
  dispatch chain, genuinely working. **Honest disclosure**: the launched
  subprocess got far enough to receive at least one real A2A response
  (`convert_a2a_message_to_event` observed in its log) before being
  deliberately killed — meaning at least one real Groq call was made during
  this verification, despite the session's instruction not to spend
  Groq/Gemini quota. This was not intentional (the test was meant to stop
  at `AGENT_STARTED`, before any LLM call), and is reported here rather
  than omitted. It also means Groq's daily quota is not currently fully
  exhausted (contrary to this session's starting assumption) — the exact
  remaining headroom is unknown. No further live-LLM verification was
  attempted after noticing this. All test processes (production, backend,
  7 agent services, the orchestrator subprocess, and their child MCP stdio
  subprocesses) were confirmed stopped afterward; `backend/.demo_logs/`
  scratch log removed.
- Verified: `npm run build` clean, root pytest (29/29) and orchestrator
  fast-logic + guardrails suites (27/27) clean after the `investigation.py`/
  `backend/app/main.py` changes.

### Dashboard visual refinement pass (2026-09, superseded by the entry above)
Note: this entry's colorful ambient-background direction was explicitly
reversed by the user immediately after — kept here only for the accurate
history of what was actually built and why it changed, per root CLAUDE.md's
"never hide failures/changes" discipline. See the entry above for the
current, real state.

User-directed warm-glass visual refresh, post-Phase-10. Full detail in
`dashboard/CLAUDE.md`. Summary:
- `dashboard/src/styles/tokens.css`/`global.css` rewritten: warm
  stone/cream/graphite palette (spec-provided hex values), 4 accent hues
  (sage/dusty-blue/dusty-peach/soft-amber) driving a new purely-decorative,
  slow-drifting ambient background (`AmbientBackground.tsx`, paused under
  `prefers-reduced-motion`), 3 glass densities (`GlassSurface`'s
  `strong`/default/new `light`), a subtle top highlight + opt-in hover lift
  (`interactive` prop).
- `RecoveryPanel` (new) replaces the old static `RecoveryPlaceholder` stub —
  renders the real `incident.recovery_plan`/`approval_state`/
  `action_history` plus whichever real `RECOVERY_PROPOSED`/
  `SAFETY_VALIDATION`/`HUMAN_APPROVAL_*`/`RECOVERY_EXECUTED`/
  `RECOVERY_VERIFIED`/`INCIDENT_RESOLVED` events have actually been emitted;
  an honest neutral empty state (never "Pending") when none exist, since
  recovery only ever triggers after a DIAGNOSED outcome.
- **Real drift bugs found and fixed while wiring this:** `dashboard/src/api/types.ts`'s
  `NexusEventType` union and `IncidentStatus` still carried the old
  pre-Phase-8 draft names (`RECOVERY_PLAN_CREATED`, `SAFETY_CHECK`,
  `HUMAN_APPROVAL_REQUIRED`, `HUMAN_APPROVED`, `RECOVERY_STARTED`/
  `COMPLETED`, `VERIFICATION_STARTED`/`COMPLETED`; `IncidentStatus` missing
  `RESOLVED`) instead of the real strings `orchestrator/recovery.py` and
  `orchestrator/investigation.py` actually emit/set. Verified by grepping
  every real `emit_event(...)` call site in both files. Fixed to match
  source exactly; `semantics.ts` gained `RESOLVED` -> green and two new
  tone mappers (`approvalDecisionTone`, `actionStatusTone`).
- Verified: `npm run build` (tsc -b + vite build) clean; manually exercised
  live in the browser pane against the real backend (production+backend
  processes, a real incident created via `POST /incidents`, a realistic
  event/state sequence posted through the real `POST /incidents/{id}/events`
  and `/state` endpoints — no live LLM call) — confirmed the ambient
  background, all 3 glass densities, the full investigation flow (agent
  cards, A2A stream, MCP activity, hypothesis constellation, critic
  challenge, decision panel) and the new `RecoveryPanel` all render
  correctly with real data. All dev/test processes stopped afterward.
- Not verified this pass: an actual live Groq-driven investigation reaching
  DIAGNOSED->RESOLVED through the dashboard (same Groq-quota constraint as
  Phase 9/10 — see "Blockers").

### Phase 10A: Full-System Integration — implemented + verified
Deterministic-only pass (no Groq/Gemini calls) over the entire Phase 1-9
uncommitted changeset. Full detail in `NEXUS_PHASE10_PLAN.md`'s 10A section;
summary:
- 126/126 deterministic tests pass across every isolated venv (backend/
  production 29, MCP 22, fast agents 27, fast orchestrator+guardrails 27,
  fault_injection 7, evaluation 14).
- `docker compose config --quiet` clean; dashboard `npm install`/`npm run
  build` now succeeds (the prior session's broken-`npm`-launcher blocker is
  gone in this environment).
- `git diff --check` clean; secret scan (diff + working tree) clean.
- **Real bug found and fixed:** `production/service.py`'s
  `resource_exhaustion` fault's random-500/latency middleware applied to
  `/admin/*` too, so the recovery action for that exact fault
  (`scale_resources`) could randomly fail because of the fault it was
  clearing. Reproduced (`tests/test_fault_recovery.py` flaked on a different
  test each of several runs pre-fix, clean 5/5 post-fix). Fix: the
  degradation now skips any `/admin`-prefixed path (NEXUS's own control
  plane), leaving customer-facing endpoints' degradation — and therefore the
  Metrics Agent's diagnostic signal — unchanged.

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

### Phase 7: Dashboard — implemented + tested
React + TypeScript + Vite app in `dashboard/`, own `package.json`/isolated
node process (no shared install with the Python venvs). Design direction
(approved by the user before any code was written): Apple Liquid Glass x
Linear x premium production-ops aesthetic — near-white/graphite, translucent
blurred "glass" surfaces with soft shadow (never glow), color reserved for
semantic state only (green/amber/red), restrained spring-based motion tied to
real state transitions only ("motion communicates causality, not
decoration") — explicitly no neon/cyberpunk/particles/glowing borders/generic
AI-SaaS styling.

- `dashboard/src/styles/tokens.css` + `global.css` — the full design-token
  system (palette, glass material, shadows, spacing, typography, motion
  durations, `prefers-reduced-motion` handling).
- `dashboard/src/components/primitives/` — `GlassSurface`, `StatusDot`,
  `Badge`, `ConfidenceBar` (Framer-Motion spring-animated fill), `MonoLabel`
  (reserved for IDs/tool names/event types only), `Timestamp`,
  `CollapsibleSection`, and `semantics.ts` (single source of truth mapping
  every real backend enum — agent runtime status, hypothesis status, critique
  verdict, incident status — to one of the 4 semantic tones).
- `dashboard/src/api/types.ts` — hand-written to mirror `docs/API_CONTRACT.md`/
  `docs/EVENT_SCHEMA.md` exactly, including the real `Critique` fallback shape
  discovered during live verification (see "Known Issues").
- `dashboard/src/api/client.ts` + `useIncident.ts` — pure `fetch` client (no
  business logic) + TanStack Query polling hooks (1.5s interval while
  `status === "INVESTIGATING"`, stops once terminal) + `deriveAgentStates`,
  which derives each diagnostic agent's IDLE/RUNNING/WAITING/COMPLETED/FAILED
  status **purely from the real event log** (AGENT_STARTED/AGENT_COMPLETED/
  MCP_TOOL_CALL/EVIDENCE_REQUESTED), never a fabricated/timed state machine.
- `dashboard/src/lib/derive.ts` — pure derivation helpers: phase index
  (DETECTED/INVESTIGATING/EVIDENCE/CRITIC/DIAGNOSIS) from which real event
  types have actually been emitted; evidence_id -> real evidence item lookup
  (resolves hypothesis evidence_ids to the actual tool/arguments/result from
  `agent_findings`, since `MCP_TOOL_RESULT` events themselves carry no result
  data — only `agent_findings` does); A2A/MCP row shaping.
- `dashboard/src/lib/recentIncidents.ts` — localStorage-backed "recently
  opened incidents" convenience for the home page. **Deliberately not backed
  by a real `GET /incidents` list endpoint** — per explicit user direction not
  to expand backend scope for this phase; each cached entry is always
  re-fetched live (`useQueries` against real `GET /incidents/{id}`), never
  treated as a source of truth.
- `dashboard/src/pages/IncidentListPage.tsx` — minimal home page exactly per
  the approved design: wordmark, live status summary line, incident-ID lookup
  box, recently-opened cards. No investigation-view content leaked in here.
- `dashboard/src/pages/InvestigationPage.tsx` + `dashboard/src/components/investigation/*`
  — the core screen, composed in the approved causal order (Incident -> 4
  diagnostic agents -> A2A -> Evidence -> Hypotheses -> Critic ->
  Re-evaluation -> Diagnosis/Abstention -> Recovery placeholder):
  - `TopBar` (sticky) + `PhaseTimeline`.
  - `AgentConstellation` / `AgentCard` x4 — real per-agent status, current MCP
    tool, evidence count.
  - `A2AStreamPanel` — operational event-stream table (timestamp/sender ->
    recipient/task_id/status), deliberately **not** chat-bubble styled.
  - `MCPActivityPanel` — tool/args/result-summary table, resolved against real
    `Finding.evidence` (no fabricated "duration" column — the real event data
    has no meaningful duration signal, an honest simplification from the
    original proposal's sketch; see "Known Issues").
  - `HypothesisPanel` — the approved centerpiece: `HypothesisSelector` (one
    hypothesis in focus at a time, others accessible via a minimal H-ID +
    compact confidence + status strip, per explicit user direction) +
    `HypothesisConstellation` (real supporting evidence on the left,
    contradicting on the right, spatially organized around the focused
    hypothesis, `layoutId`-based entrance/reflow animation) + `RevisionBanner`.
  - `CriticChallengePanel`, `ReEvaluationLoopIndicator` ("Cycle N of M" from
    real `RE_EVALUATION_STARTED` payloads).
  - `DecisionPanel` — diagnosis and abstention rendered with equal visual
    weight (same component/transition, differing only in semantic color/copy)
    — abstention reads as a deliberate engineering outcome, not an error
    screen, per the approved copy ("NO SUFFICIENTLY SUPPORTED ROOT CAUSE" /
    "Investigation terminated after N evaluation cycles.").
  - `RecoveryPlaceholder` — visible but disabled (Phase 8), never wired to
    fabricated data.
  - `UsagePanel` — real, designed "Unavailable from provider" empty state
    (root CLAUDE.md section 8) — no token/usage metadata exists anywhere in
    the Phase 6 pipeline to display.
- `.claude/launch.json` — added `nexus-dashboard` config (`npm --prefix
  dashboard run dev`, port 5173) for previewing the dev server.

### Phase 8: Guardrails + Recovery — implemented + tested
Built from scratch (`guardrails/`, `agents/recovery/` were empty except a
stub `CLAUDE.md`) following the exact structural-enforcement pattern Phase 6
established for Evidence/Critic, plus a brand-new mutable-state layer in
`production/` (Phase 1/2/6/7 gave NEXUS nothing that could actually get
better, only things that could be read).

- `production/state.py` (new) — the only mutable state in `production/`:
  thread-safe flags for the 5 fault types (`bad_deployment`, `db_slowdown`,
  `config_error`, `dependency_failure`, `resource_exhaustion`) plus
  `deployed_version`. `restart_service()`/`rollback_deployment()`/
  `reset_config()`/`scale_resources()` are the 4 real recovery-action
  mutators; `inject()`/`clear_all()` are fault-injection-only (Phase 9 uses
  these too).
- `production/service.py` — real symptom logic consulting `state.py` on
  every request: `resource_exhaustion` adds real middleware-level latency +
  an 8% real 500 chance on every endpoint; `config_error` makes `/orders`
  and `/orders/{id}` fail deterministically (100%, not flaky) with a
  `ConfigError` message; `bad_deployment` makes them fail ~35% of the time
  with an `OrderServiceError` message; `dependency_failure` adds real ~1.5s
  latency + a 50% `DependencyTimeoutError` on `/orders/{id}` only.
  `db.py`'s `run_query()` now really sleeps `DB_SLOWDOWN_SECONDS` (0.25s)
  while `db_slowdown` is set. New mutating admin endpoints:
  `GET /admin/state`, `POST /admin/fault/inject`, `POST /admin/fault/clear`,
  `POST /admin/recovery/{restart_service,rollback_deployment,reset_config,
  scale_resources}` — only `fault_injection/injector.py` and
  `guardrails/production_client.py` are expected to call these.
- `production/changes.py` — `append()` (new): called for real by both a
  `bad_deployment` fault injection and a `rollback_deployment` recovery
  action, so both leave a genuine entry in the same change-history timeline
  the Change Analysis Agent already queries. `recent()`'s sort fixed to
  tie-break equal-second timestamps by insertion order (a real bug caught by
  `tests/test_fault_recovery.py` on first run — two admin calls landing in
  the same wall-clock second were coming back in the wrong order).
- `guardrails/config.py`, `production_client.py`, `audit.py`,
  `kill_switch.py`, `policy.py`, `executor.py` (all new) — the safety layer.
  `config.ALLOWED_ACTIONS` is the one authoritative allowlist (4 actions:
  `restart_service`, `rollback_deployment`, `reset_config`,
  `scale_resources`, each bound to one admin endpoint + required params +
  risk level + blast radius). `policy.validate_plan()` is a second,
  independent, deterministic (no LLM) gate that re-validates every
  action/param/risk_level from scratch — rejects the WHOLE plan on ANY
  violation, never silently drops the bad part. `kill_switch.py` is
  file-based (`guardrails/.kill_switch`, gitignored), re-checked live before
  EVERY action in `executor.execute_plan()`, not just once per plan. No
  dedicated venv — only dependency is `httpx`, already pinned in
  `orchestrator/requirements.txt`; guardrails imports run inside
  `.venv-orchestrator/`.
- `agents/recovery/agent.py`, `a2a_service.py`, `__init__.py` (new) —
  Recovery Agent (port 8107), same `ReasoningAgent`-based pattern as
  Evidence/Critic: **zero MCP tools, zero execution capability**.
  `build_recovery_plan()` drops any action outside its own local
  `ACTION_CATALOG` (a separate, non-authoritative copy of the same 4 action
  names, used only to constrain the prompt) and normalizes an invalid
  `risk_level` to `MEDIUM`. Its prompt explicitly requires copying a real
  `target_version` string verbatim from the `evidence_pool` it's given for
  `rollback_deployment`, and to omit that action entirely if no deployment
  history is present — verified live (see below) that the model actually
  follows this rather than inventing a version number.
- `agents/common/ports.py` — `+recovery_agent: 8107`.
- `orchestrator/recovery.py` (new) — `run_recovery(incident_id, hypothesis,
  critique, evidence_pool) -> dict`: the full bounded flow (propose ->
  validate -> request+wait-for human approval, bounded by
  `MAX_APPROVAL_WAIT_SECONDS`/env, default 120s -> execute -> verify via a
  real second A2A call to the Metrics Agent -> RESOLVED only on verified
  success). Every branch (`REJECTED_BY_SAFETY_VALIDATION`,
  `APPROVAL_EXPIRED`, `REJECTED_BY_HUMAN`, `EXECUTION_FAILED`,
  `VERIFICATION_FAILED`, `RESOLVED`) persists to `backend/` and is a
  legitimate stopping point, not an exception — recovery can fail safely at
  any stage without corrupting incident state.
- `orchestrator/investigation.py` — `run_investigation()` gained
  `trigger_recovery: bool = True` and `skip_critic: bool = False` params.
  On a `DIAGNOSED` decision (and `trigger_recovery=True`, the default),
  automatically calls `recovery.run_recovery()` with the leading hypothesis,
  the critique that supported it, and the flattened real evidence pool.
  `skip_critic=True` (Phase 9 ablation arm) accepts the leading hypothesis as
  DIAGNOSED with a synthetic "critic skipped" critique and **zero** real A2A
  calls to `root_cause_critic` — a genuine ablation, not a simulated one.
- `backend/app/main.py` — `POST /incidents/{id}/approve` (new):
  `{"decision": "APPROVED"|"REJECTED", "approved_by": str}` -> records
  `approval_state`, appends `HUMAN_APPROVAL_GRANTED`/`REJECTED`. Persistence
  only, per `backend/CLAUDE.md`'s "no business logic here" rule — it never
  decides anything, only records a decision a human already made outside
  this process.
- `docs/EVENT_SCHEMA.md` — reconciled: the file previously used a different
  draft naming (`RECOVERY_PLAN_CREATED`, `SAFETY_CHECK`,
  `HUMAN_APPROVAL_REQUIRED`, `HUMAN_APPROVED`, split
  `RECOVERY_STARTED`/`COMPLETED` and `VERIFICATION_STARTED`/`COMPLETED`)
  that conflicted with root `CLAUDE.md` section 16's canonical event names —
  renamed to match root `CLAUDE.md` exactly (`RECOVERY_PROPOSED`,
  `SAFETY_VALIDATION`, `HUMAN_APPROVAL_REQUESTED`, `HUMAN_APPROVAL_GRANTED`,
  `RECOVERY_EXECUTED`, `RECOVERY_VERIFIED`, `INCIDENT_RESOLVED`), plus an
  intentional addition (`HUMAN_APPROVAL_REJECTED`) since a human explicitly
  rejecting a plan is a distinct real outcome root CLAUDE.md's list doesn't
  separately name. `docs/API_CONTRACT.md` updated with the approve endpoint,
  the full recovery-flow contract, the 4 admin endpoints, and the Recovery
  Agent's A2A topology entry (port 8107).
- Also fixed 3 stale phase-number references in `guardrails/CLAUDE.md`,
  `fault_injection/CLAUDE.md`, `evaluation/CLAUDE.md` (they said Phase
  9/10/10-11 respectively, from an older numbering draft that conflicted
  with this file's "Phase 8"/"Phase 9" framing — root CLAUDE.md section 24
  is the canonical numbering; this file follows it).

**Tests:** `guardrails/tests/test_policy_executor.py` (new, 14 fast
deterministic unit tests, no network — `production_client.post` monkeypatched
at its own module boundary): every `validate_plan` rejection/approval path,
`execute_plan`'s ordering/kill-switch-mid-execution/stop-on-first-failure/
param-dropping/refuse-non-allowlisted-action behavior, kill switch
engage/disengage round trip. `agents/tests/test_recovery.py` (new, 6 tests,
same `importlib`-by-path pattern `test_evidence_critic.py` already uses for
the `agent.py` name collision across `evidence/`/`critic/`/`recovery/`):
valid actions pass through, invented actions dropped, invalid risk_level
falls back to MEDIUM, action list capped, non-dict model output doesn't
crash, missing hypothesis_id stays `None` not fabricated.
`orchestrator/tests/test_recovery_logic.py` (new, 6 tests, same
network-boundary-monkeypatching philosophy as `test_investigation_logic.py`):
safety-validation rejection stops before any approval request, approval
expiry never executes, human rejection never executes, a fully approved plan
executes+verifies+resolves, execution failure never claims RESOLVED,
verification failure after successful execution never claims RESOLVED.
`orchestrator/tests/test_investigation_logic.py` — 2 new tests (DIAGNOSED
triggers the recovery hook exactly once with the right hypothesis/critique;
ABSTAINED never touches it; `skip_critic=True` reaches DIAGNOSED with zero
critic calls, and abstains correctly with zero hypotheses).
`tests/test_incidents.py` — 4 new tests for the approve endpoint.
`tests/test_fault_recovery.py` (new, 11 tests against the real
`production/` `TestClient` app, no mocking): every fault's real symptom,
every recovery action's real state mutation, admin-state/clear/400-on-unknown
paths. **All of the above pass**: 14+6+6+2+4+11 = 43 new tests, plus the full
prior regression suite (78 fast/protocol tests across backend+production,
mcp, and fast agents/orchestrator suites) still passes unchanged.

**Real live verification performed in this session (not simulated):**
started `production/` (8001), `backend/` (8000), and all 7 real A2A services
(8101-8107, including the new `recovery_agent` on 8107 — confirmed
independently listening via `.well-known/agent-card.json` returning 200 on
every port). Then:
1. Injected the real `bad_deployment` fault and drove real traffic against
   `/orders` — confirmed a real elevated error rate and a real new
   `/changes` entry (`author: "fault_injection"`).
2. Ran a real full `run_investigation()` against the live stack. Only
   `database_agent` responded within the parallel dispatch window; the
   other 3 diagnostic agents hit `litellm.RateLimitError` — the Groq
   account's **daily** token quota (TPD 200000) was already near-exhausted
   (199112-199729/200000 used across this session's calls) before this run
   even started, a pre-existing condition from this same session's own
   verification traffic, not a new defect. The run correctly reached
   `ABSTAINED` (`"no open hypothesis left to evaluate"`) rather than forcing
   a diagnosis from the one thin, irrelevant finding it did get — the
   bounded-loop/abstain-rather-than-force guarantee held under a genuine
   real-world failure mode it wasn't specifically designed for.
3. Called the real Recovery Agent directly over A2A (bypassing the
   just-exhausted parallel-dispatch path) with a hand-built
   hypothesis+critique and **no** `evidence_pool`: it correctly proposed
   `rollback_deployment` but with **no** `target_version` (correctly
   refusing to invent one, per its instruction) — `guardrails.policy.
   validate_plan()` would correctly REJECT this (missing required param),
   which is exactly the intended defense-in-depth behavior, not a bug. Given
   the same evidence_pool WITH a real `get_recent_deployments`-shaped
   deployment history, this exact gap is what motivated adding
   `evidence_pool` to the Recovery Agent's payload (see "Phase 8" above) —
   the fix was made in this same session, but re-verifying the corrected
   prompt live was blocked by full TPD exhaustion immediately afterward
   (confirmed: 199729/200000 used, next call failed outright). **Honest
   status: the Recovery Agent's real Groq/A2A round trip is verified live
   for the pre-fix prompt; the post-fix prompt (requiring a real
   target_version from evidence_pool) is unit-tested but not yet verified
   against a live Groq call** — flagged, not claimed.
4. Ran the full recovery execution path for real, with no LLM involved:
   built a valid `rollback_deployment` plan by hand, ran it through the
   real `guardrails.policy.validate_plan()` (APPROVED_FOR_HUMAN_REVIEW) and
   the real `guardrails.executor.execute_plan()` against the live
   `production/` service — it genuinely called
   `POST /admin/recovery/rollback_deployment`, genuinely flipped
   `bad_deployment` back to `false`, genuinely fixed `GET /orders` (500 ->
   200), and genuinely appended a `"author": "guardrails"` change-history
   entry. This is real, verified end-to-end proof of the execution/safety
   mechanism independent of the Groq quota issue.
5. Verified the kill switch live: injected `resource_exhaustion`, engaged
   the kill switch (`guardrails/kill_switch.py engage`), attempted to
   execute a `scale_resources` action — correctly returned
   `SKIPPED_KILL_SWITCH` and never called `production/` at all. Disengaged,
   cleared the fault.
6. All processes killed, kill switch sentinel removed, ports confirmed free.

### Phase 9: Fault Injection + Evaluation — implemented + unit-tested; live benchmark blocked
- `fault_injection/scenarios.py` (new) — `SCENARIOS`: the 5 minimum failure
  classes from `docs/EVALUATION.md`, each with the exact schema root
  CLAUDE.md section 19 requires, each `fault_type` mapping 1:1 onto
  `production/state.FAULT_TYPES`. `get_ground_truth(scenario_id)` is the ONE
  function meant to be called for scoring — returns only
  `{scenario_id, ground_truth_root_cause, recovery_expectation}`, never the
  full scenario (which would leak `expected_symptoms` hints).
- `fault_injection/injector.py` (new) — bounded HTTP client to
  `production/`'s `/admin/fault/*` endpoints only. Separate module from
  `guardrails/production_client.py`/`mcp/production_client.py` (dependency
  isolation).
- `evaluation/production_reader.py` (new) — bounded read-only HTTP client
  used ONLY by the single-agent baseline: one flat snapshot
  (metrics+logs+changes+db diagnostics), not iterative tool access — this is
  what makes it "single-agent, no tool loop."
- `evaluation/baselines.py` (new) — `single_agent_baseline()`: ONE real
  Groq/GPT-OSS-120B `litellm.completion` call (no ADK, no tools, no
  multi-agent coordination) given one evidence snapshot. `build_result()` is
  the structural enforcement mirroring every other `build_*` in this system
  — an out-of-catalog `root_cause` normalizes to `"unknown"`.
- `evaluation/scoring.py` (new) — pure functions, no network:
  `classify_statement()` (keyword-maps a NEXUS Hypothesis's free-text
  statement onto the closed root-cause vocabulary, for scoring only, never
  fed back into any agent), `score_run()`/`aggregate()` (root-cause accuracy,
  false diagnosis rate, abstention rate, diagnosis rate, avg latency).
- `evaluation/run_experiment.py` (new) — the actual benchmark driver: per
  scenario, inject the real fault, run all 3 comparison arms
  (`single_agent_baseline`; `full_nexus` = `run_investigation(...,
  trigger_recovery=False)`; `nexus_no_critic` = same with
  `skip_critic=True`), clear the fault, score against ground truth, write a
  JSON report to `evaluation/results/` (gitignored).

**Tests:** `fault_injection/tests/test_scenarios.py` (new, 5 pure unit
tests): every scenario's `fault_type` is real, all 5 failure classes covered
exactly once, every scenario has the required schema fields,
`get_ground_truth` exposes only the 3 intended keys, unknown scenario_id
raises. `fault_injection/tests/test_injector_live.py` (new, 2 real tests
against a live `production/` instance — **run for real in this session**,
both passed: inject+clear `bad_deployment` round trip, `current_state()`
reflects a real `db_slowdown` injection). `evaluation/tests/test_scoring.py`
(new, 11 pure unit tests): keyword classification for all 5 fault types +
unknown fallback, correct/false/abstained/neutral-unknown scoring branches,
`aggregate()`'s rates over a mixed batch and the empty-list case,
`baselines.build_result`'s out-of-catalog/confidence-clamping/unparseable-
output handling.

**Live benchmark run: not completed — honestly blocked, not skipped.**
`evaluation/run_experiment.py` was written and its every pure/logic
component is unit-tested, but running it end-to-end across all 5 scenarios
(which needs 1 baseline Groq call + 2 full orchestrator runs per scenario =
~15 more real Groq calls minimum) was not attempted after Phase 8's live
verification (above) confirmed the account's daily token quota (TPD 200000)
was fully exhausted (199729/200000 used, the next call failed outright).
Attempting it anyway would either hang retrying or immediately fail every
arm, producing a report of all-failures that would misrepresent the code's
actual correctness — reporting that as "the benchmark ran" would violate
root CLAUDE.md section 26 ("never claim untested work is complete") and
section 21 ("never fabricate metrics"). See "Blockers" below for what
unblocks this.

## In Progress
Nothing in flight. Phase 10 (10A-10D) complete for this session's scope —
see `NEXUS_PHASE10_PLAN.md`. Two items remain, both gated on live Groq quota,
not on missing code (see "Next" and "Blockers").

## Next
- Run `docs/DEMO_RUNBOOK.md` step 4 for real
  (`orchestrator/run_demo.py "..."`) once Groq daily quota has headroom —
  this is the one remaining unverified step in an otherwise fully
  live-verified (non-LLM parts) end-to-end demo procedure.
- Re-run the Phase 9 live benchmark (`evaluation/run_experiment.py`) once the
  Groq account's daily token quota resets — this is the single concrete
  unblock for "run the actual experiments/evaluation" being fully complete,
  not just implemented+unit-tested. No code changes anticipated; the runner,
  scoring, and all 3 arms already exist and are unit-tested.
- Re-verify the Recovery Agent's post-`evidence_pool`-fix prompt against a
  real live Groq call once quota resets (see "Phase 8" above) — the fix
  itself is real and unit-tested; only the live re-confirmation is pending.
- Wire the dashboard's `RecoveryPlaceholder` (Phase 7, currently disabled) to
  the real Phase 8 events/state (`recovery_plan`, `approval_state`,
  `action_history`, the `RECOVERY_*`/`SAFETY_VALIDATION`/`HUMAN_APPROVAL_*`
  event types) — not attempted this session; Phase 8/9 scope was
  backend/orchestrator/agents/guardrails, not the dashboard.
- Consider a small UI (or just documenting the exact curl command) for
  calling `POST /incidents/{id}/approve` — today it's a real endpoint with no
  human-facing surface other than a direct HTTP call or a future dashboard
  panel.
- `GET /incidents` list endpoint: deliberately deferred (see Phase 7 above) —
  a small, additive backend enhancement once/if requested; the home page's
  localStorage-based recent-incidents list works without it in the meantime.
- SSE/websocket streaming: the dashboard ships on polling (1.5s) by design for
  this phase — `useIncidentEventsQuery`/`useIncidentQuery` are structured so a
  push-based transport is a drop-in swap inside those two hooks only, without
  touching any component, if a future phase needs true push.
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
- **Dashboard: `Critique` objects from the real backend do not always match
  the full documented schema — caught live during Phase 7 verification, not
  guessed.** `orchestrator/investigation.py`'s `_call_critic()` falls back to
  a minimal `{critique_id: None, hypothesis_id, verdict: "INSUFFICIENT_EVIDENCE",
  rationale}` object when the Root-Cause Critic's real A2A response is
  unparseable — which bypasses `agents/critic/agent.py`'s `build_critique()`
  structural enforcement entirely (that function always produces the full
  shape; this fallback path in `investigation.py` does not). This is a real
  path, not a hypothetical: it was hit during Phase 7's live verification run
  when the Groq account's daily token quota (TPD) was exhausted mid-investigation,
  causing every subsequent real critic call to fail and fall back. The
  dashboard's `CriticChallengePanel`/`RevisionBanner` originally assumed the
  full `Critique` shape and crashed (`Cannot read properties of undefined
  (reading 'length')`) on the missing `contradictions`/`requested_evidence`/
  `alternative_explanations` arrays. **Fixed:** `dashboard/src/api/types.ts`'s
  `Critique` interface now marks every field beyond
  `hypothesis_id`/`verdict`/`rationale` as optional (matching what the backend
  actually guarantees, not the aspirational full schema), and
  `CriticChallengePanel.tsx`/`RevisionBanner.tsx` read every optional array
  defensively (`?? []`). Not a `backend/`/`orchestrator/`/`agents/` change —
  the real fallback behavior there is itself reasonable (never crash the
  investigation loop over an unparseable critic reply); the dashboard just
  needed to not over-assume the schema. Confirmed fixed by reloading the
  dashboard against the same live (already-abstained) incident state.
- **Dashboard: `RevisionBanner` design deviation from the originally-approved
  mockup (a concrete technical constraint, not a preference change).** The
  approved design sketch showed a same-hypothesis confidence delta ("Previous
  confidence: 78% -> 41%"). Real data does not support this:
  `agents/evidence/agent.py`'s `build_hypotheses()` hardcodes
  `"revision": 1` (never incremented) and reassigns `hypothesis_id` fresh
  (`H1`, `H2`, ... by descending confidence) on every Evidence Agent call,
  including every re-investigation round — so a hypothesis's `confidence`
  never actually changes in place, and a hypothesis_id is not a stable
  identity across rounds. Fabricating a cross-round confidence delta by
  fuzzy-matching on `statement` text was considered and rejected as inventing
  a correlation the backend doesn't establish. **Substituted:** the banner
  shows the real signal that does exist — the critic's actual verdict
  (`PROPOSED -> <status>`) plus its real `rationale`/`contradictions` text —
  which is what actually happens in the system when a hypothesis is
  challenged. Documented in `RevisionBanner.tsx`'s own docstring.
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
- **Groq daily token quota (TPD 200000), not just the per-minute (TPM 8000)
  limit already documented above, was hit for the first time in Phase 8's
  live verification session** — a 4-agent parallel dispatch during this
  session's live `run_investigation()` run got only 1/4 real responses
  (`database_agent`); the other 3 hit `litellm.RateLimitError` reporting the
  TPD limit, not TPM. `litellm.num_retries=5`'s backoff (seconds) cannot
  absorb a daily quota needing 10+ minutes to partially replenish — this is
  a different failure mode from the TPM issue and isn't fixed by the
  existing retry config. Not a code defect; see "Blockers". The
  `ABSTAINED`-not-forced outcome this produced is itself a genuine (if
  unplanned) validation of the loop's abstain-rather-than-force guarantee.
- **The Recovery Agent initially had no way to name a real `target_version`
  for `rollback_deployment`** because `orchestrator/recovery.py` only passed
  it `hypothesis`+`critique`, not the real evidence pool — caught live in
  this session (see "Phase 8" and "Important Decisions" above), fixed by
  threading `evidence_pool` through `run_recovery()`/`_call_recovery_agent()`
  into the agent's A2A payload and tightening its instruction. The fix
  itself is unit-tested; re-verifying it against a live Groq call is
  pending the Groq quota reset (see "Blockers") — flagged, not claimed as
  re-verified.

## Important Decisions
- **The Recovery Agent has zero execution capability by construction, not by
  prompt discipline alone.** `agents/recovery/agent.py`'s `RecoveryAgent` is
  `ReasoningAgent`-based (`tools=[]`) — it cannot call anything in
  `production/` even if it wanted to. `guardrails/` (deterministic Python,
  no LLM) is the only code path that ever calls a mutating endpoint, and it
  independently re-validates every proposed action against its own
  authoritative allowlist (`guardrails/config.ALLOWED_ACTIONS`) rather than
  trusting `agents/recovery/agent.py`'s own local `ACTION_CATALOG`. This is
  root CLAUDE.md section 20's "never execute arbitrary shell commands
  generated by an LLM" made structurally true, the same way Phase 4's
  observation/interpretation split and Phase 6's evidence-id/verdict
  enforcement made their respective guarantees structural rather than
  prompt-only.
- **Recovery approval is a real, bounded poll against a real human action,
  not a simulated wait.** `orchestrator/recovery.py`'s
  `_wait_for_human_approval()` polls `backend/`'s real `GET /incidents/{id}`
  for a change made by a real out-of-band `POST /incidents/{id}/approve`
  call — there is no code path that can grant its own approval. Bounded by
  `MAX_APPROVAL_WAIT_SECONDS` (env, default 120s) so an unanswered approval
  request expires rather than hanging the investigation forever, mirroring
  `MAX_REEVALUATION_LOOPS`'s "never an infinite autonomous loop" principle
  applied to a human-in-the-loop wait instead of an LLM loop.
- **Kill switch is file-based, not env-var-based, and re-checked before every
  single action, not once per plan.** A sentinel file
  (`guardrails/.kill_switch`, gitignored) can be toggled without restarting
  any process — verified live: engaging it mid-plan correctly halted
  execution before the next action with zero calls to `production/` for
  that action.
- **Recovery verification re-uses the existing Metrics Agent over a real
  second A2A call rather than a new direct HTTP check from
  `orchestrator/`.** Keeps `orchestrator/`'s existing rule intact ("do not
  mutate/query infrastructure directly; only through `mcp/` tools invoked by
  agents") — recovery verification is evidence-gathering, so it goes through
  the same real-A2A-to-a-real-diagnostic-agent path every other piece of
  evidence in the system already uses, rather than opening a new,
  architecturally inconsistent code path.
- **`agents/recovery/agent.py` needs the real evidence pool (the same one
  the critic sees), not just the hypothesis+critique, to name a real
  `target_version` for `rollback_deployment`.** Discovered live in this
  session (see "Phase 8" above): without it, the model correctly refused to
  invent a version number, which `guardrails/policy.py` then correctly
  rejected for a missing required param — the safety gate did exactly what
  it should, but the plan was needlessly rejected because the agent lacked
  the one piece of real evidence it needed. Fixed by threading the
  flattened evidence pool through `orchestrator/recovery.py`'s
  `run_recovery(..., evidence_pool=...)` into the Recovery Agent's A2A
  payload, and tightening its instruction to require copying a version
  string verbatim from `evidence_pool` or omitting the action entirely.
- **`docs/EVENT_SCHEMA.md`'s recovery/approval/verification event names were
  renamed to match root CLAUDE.md section 16 exactly at implementation
  time**, not left as an earlier draft's different naming — see "Phase 8"
  above for the exact before/after mapping. Root CLAUDE.md is the
  non-negotiable master spec; a docs file that drifted from it had to be the
  one that changed.
- **Evaluation's 3 comparison arms all run through
  `orchestrator/investigation.run_investigation()`'s real parameters
  (`trigger_recovery=False`, `skip_critic=True`) rather than separate
  reimplementations of the investigation loop.** A hand-written "ablation"
  copy of the loop would risk silently drifting from the real loop's actual
  behavior over time; reusing the real function with a real flag guarantees
  the ablation arm is measuring an actual property of the real system, not
  an approximation of it.
- **`evaluation/`'s single-agent baseline uses raw `litellm.completion`
  directly, not an ADK `Agent`.** There is no multi-turn/tool-calling loop
  in a one-shot baseline call, so ADK's `LiteLlm`/`Agent`/`InMemoryRunner`
  machinery (needed for the Groq reasoning-content multi-turn bug's fix)
  isn't actually exercised here — using it anyway would be unnecessary
  weight for a component whose whole point is being the simplest possible
  comparison point.
- Tech stack: Python 3.11 + FastAPI + asyncio for backend/production; **Google
  ADK (Python)** for orchestrator/agents; **official `mcp` Python SDK (2.x)** for
  `mcp/`; **official `a2a-sdk` (1.x)** for A2A. Dashboard (Phase 7): **React +
  TypeScript + Vite**, hand-rolled CSS tokens/CSS Modules (no Tailwind/component
  library — the Liquid Glass visual language is bespoke), **Framer Motion**
  (spring-based, state-driven animation only), **TanStack Query** (polling,
  structured to swap for push/SSE later without touching components),
  **React Router**. Own `package.json`/node install, isolated from every
  Python venv, per root CLAUDE.md section 23's dependency-isolation principle.
- **Dashboard ships on polling, not SSE/websocket, for Phase 7 — a deliberate
  scope decision, not an oversight.** `backend/` remains poll-only
  (`GET /incidents/{id}`, `GET /incidents/{id}/events`); adding push transport
  is backend work outside a frontend phase's smallest-safe-change scope.
  `useIncidentQuery`/`useIncidentEventsQuery` (`dashboard/src/api/useIncident.ts`)
  isolate the polling mechanism behind two hooks specifically so a future swap
  to SSE/websocket touches only those two functions.
- **No `GET /incidents` list endpoint added in Phase 7 — explicit user
  direction** ("don't expand backend scope just to make the UI prettier").
  The home page instead uses a localStorage-based "recently opened incidents"
  convenience (`dashboard/src/lib/recentIncidents.ts`) that always re-fetches
  real live state; add the real endpoint only when asked.
- **Hypothesis focus model: one hypothesis in focus at a time, others reachable
  via a minimal selector strip — explicit user direction**, not a default
  Claude chose. Multiple simultaneous constellations were explicitly rejected
  as visual noise unless a genuine comparison need arises later.
- **UsagePanel intentionally shows a designed "Unavailable from provider"
  empty state, never fabricated numbers** (root CLAUDE.md section 8) — no
  token/usage metadata is captured anywhere in the Phase 6 pipeline yet.
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

```bash
# Phase 7 (dashboard):
cd dashboard
npm install
npx tsc -b        # typecheck
npm run build     # production build (vite build)
npm run dev        # dev server, http://localhost:5173, proxies /api -> :8000
```
Last full run (2026-09-18, Phase 7): dashboard typecheck clean, production
build clean (`vite build` succeeded, 344KB JS / 15KB CSS gzipped to ~111KB).
Backend/production Phase 1/2 regression re-run **14/14 passed** (unchanged —
confirms Phase 7 did not touch backend/production). Fast Python suites not
requiring live Groq calls: `agents/tests/test_finding.py` +
`test_evidence_critic.py` **21 passed**; `orchestrator/tests/test_investigation_logic.py`
**4 passed** (monkeypatched, no network); `mcp/tests` **22 passed** (needs
`production/` running, no LLM). Real-LLM suites
(`test_agents_integration.py`, `test_a2a.py`'s real round-trip cases,
`test_incident_manager.py`, `test_investigation_e2e.py`) were **not re-run**
in this session — not skipped by choice, but blocked by the Groq account's
daily token quota (TPD 200000) being exhausted during the live verification
run below; these suites already passed in the Phase 6 session (see above) and
nothing in `agents/`/`orchestrator/`/`mcp/`/`backend/` was modified in Phase
7, so no regression is expected — flagged honestly rather than claimed as
re-verified.

**Live end-to-end dashboard verification (real stack, not mocked):** started
`production/` (8001), `backend/` (8000), and all 6 real A2A services
(8101-8106), then drove one real investigation
(`orchestrator/investigation.py`'s `run_investigation()`) end-to-end against
them, then loaded the dashboard (`npm run dev`, port 5173) in a real browser
against that live incident (`INC-5a3d8729`) throughout its actual lifecycle:
- Home page rendered per the approved minimal design.
- `AgentConstellation` showed real per-agent status transitioning
  IDLE -> RUNNING/COMPLETED/**FAILED** live — the FAILED case (Logs & Traces,
  then later Metrics/Change Analysis too, once the Groq TPD quota was
  exhausted) rendered correctly in red, an unplanned but genuine validation of
  the FAILED semantic-tone path against a real failure, not a synthetic one.
- `A2AStreamPanel`/`MCPActivityPanel` rendered real sender/recipient/task_id
  rows and real tool/arguments/result rows.
- `HypothesisPanel`'s constellation rendered 3 real hypotheses (H1/H3/H2) with
  real supporting/contradicting evidence nodes spatially organized left/right
  around the focused hypothesis, and a real 62% confidence bar.
- The investigation reached a real `ABSTAINED` decision
  (`"no open hypothesis left to evaluate"`, 2/3 loops used) after the Groq
  daily quota was exhausted mid-run and the Critic's A2A response became
  unparseable. This **surfaced a real dashboard bug** (see Known Issues:
  `CriticChallengePanel`/`RevisionBanner` crashing on the resulting minimal
  fallback `Critique` object) — fixed, and the fix was verified by reloading
  the dashboard against the same live incident state with no crash and
  correct rendering (`H1 · INSUFFICIENT_EVIDENCE · "critic A2A call returned
  no parseable response"`).
- `DecisionPanel` rendered the abstention exactly per the approved copy:
  "NO SUFFICIENTLY SUPPORTED ROOT CAUSE" / "Investigation terminated after 2
  evaluation cycles."
- No console errors after the fix (verified via `read_console_messages`); DOM
  tree verified single-instance/correctly-ordered via `read_page` (an earlier
  apparent "duplicate TopBar" was a scaled-screenshot misread, confirmed benign
  via `getComputedStyle` — sticky positioning (`top: 16px`) works correctly).
- All manually-started processes (production, backend, 6 A2A services,
  dashboard dev server) killed after verification; ports confirmed free.

```bash
# Phase 8/9:
python -m pytest guardrails/tests -q                              # 14, no network
.venv-agents/Scripts/python -m pytest agents/tests/test_recovery.py -q   # 6, no network
.venv-orchestrator/Scripts/python -m pytest orchestrator/tests/test_investigation_logic.py orchestrator/tests/test_recovery_logic.py -q  # 13, no network
.venv/Scripts/python -m pytest tests/test_fault_recovery.py tests/test_incidents.py -q  # 15, no network
python -m pytest fault_injection/tests/test_scenarios.py -q        # 5, no network
.venv-orchestrator/Scripts/python -m pytest evaluation/tests -q   # 11, no network
# needs production/ running:
python -m pytest fault_injection/tests/test_injector_live.py -q   # 2, real
```
Last full run (2026-09-18, Phase 8/9): every suite above passed
(14+6+7+4+11+5+11+2 = 60 new tests, plus the full prior regression: backend+
production 29/29 including the new `test_fault_recovery.py`, mcp 22/22,
agents fast suites 27/27, orchestrator fast suites 13/13 — no regressions).
Live, non-simulated verification against a real running `production/` +
`backend/` + all 7 A2A services (Recovery Agent real Groq/A2A round trip,
real guardrails execute-plan against live `production/`, real kill-switch
mid-execution halt, real fault-injection symptom generation) is documented
in full under "Phase 8" above. The one item NOT completed: a full live
`evaluation/run_experiment.py` benchmark run, blocked by Groq TPD exhaustion
— see "Blockers".

## Recent Files (Phase 8/9)
- production/state.py (new); production/service.py (fault symptoms + 7
  admin endpoints); production/db.py (+db_slowdown latency);
  production/changes.py (+append(), tie-break sort fix)
- guardrails/config.py, production_client.py, audit.py, kill_switch.py,
  policy.py, executor.py, requirements.txt (all new); guardrails/tests/
  test_policy_executor.py (new)
- agents/recovery/agent.py, a2a_service.py, __init__.py (new);
  agents/common/ports.py (+recovery_agent: 8107); agents/tests/
  test_recovery.py (new)
- orchestrator/recovery.py (new); orchestrator/investigation.py
  (+trigger_recovery, +skip_critic params, recovery hook);
  orchestrator/tests/test_recovery_logic.py (new);
  orchestrator/tests/test_investigation_logic.py (+2 tests)
- backend/app/main.py (+POST /incidents/{id}/approve); tests/test_incidents.py
  (+4 tests)
- fault_injection/scenarios.py, injector.py, requirements.txt (all new);
  fault_injection/tests/test_scenarios.py, test_injector_live.py (new)
- evaluation/production_reader.py, baselines.py, scoring.py,
  run_experiment.py, requirements.txt (all new); evaluation/tests/
  test_scoring.py (new)
- tests/test_fault_recovery.py (new)
- docs/EVENT_SCHEMA.md (recovery event names reconciled to root CLAUDE.md),
  docs/API_CONTRACT.md (approve endpoint, admin endpoints, recovery flow
  contract, recovery_agent A2A topology), guardrails/CLAUDE.md,
  fault_injection/CLAUDE.md, evaluation/CLAUDE.md (rewritten from stubs),
  agents/CLAUDE.md, orchestrator/CLAUDE.md, backend/CLAUDE.md,
  production/CLAUDE.md (all updated)
- .gitignore (+guardrails/.kill_switch, +evaluation/results/)

## Recent Files (Phase 7)
- dashboard/ (new) — full Vite/React/TypeScript app: `package.json`,
  `tsconfig*.json`, `vite.config.ts` (proxies `/api` -> `http://127.0.0.1:8000`),
  `index.html`, `src/main.tsx`, `src/App.tsx`, `src/styles/{tokens,global}.css`,
  `src/api/{types,client,useIncident}.ts`, `src/lib/{derive,recentIncidents}.ts`,
  `src/components/primitives/*` (8 files), `src/components/investigation/*`
  (16 files), `src/pages/{IncidentListPage,InvestigationPage}.tsx` (+ CSS
  Modules for each).
- dashboard/CLAUDE.md — rewritten with real Phase 7 ownership/status (was
  stale: previously said "Phase 8" for the dashboard's own phase number).
- .claude/launch.json (new) — `nexus-dashboard` dev-server config.
- docs/PROJECT_STATE.md — this Phase 7 entry.
- No files changed under `backend/`, `production/`, `agents/`, `orchestrator/`,
  `mcp/` — Phase 7 is dashboard-only, confirmed by the unchanged Phase 1/2/6
  regression results above.

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
The Groq account's daily token quota (TPD 200000) is exhausted as of this
session's end (199729+/200000 used — Phase 7's prior exhaustion had already
consumed most of it; this session's Phase 8 live verification calls used the
rest). This blocks, until it resets:
- Re-running any real-LLM Python test suite (`test_agents_integration.py`,
  `test_a2a.py`'s real round-trip cases, `test_incident_manager.py`,
  `test_investigation_e2e.py`) — unchanged from Phase 7's note, still true.
- Completing a full live `run_investigation()` pass through all 4 diagnostic
  agents without at least one hitting `RateLimitError` (Phase 8's live run
  in this session got only 1/4 agents to respond for exactly this reason).
- Re-verifying the Recovery Agent's `evidence_pool`-aware prompt fix against
  a real Groq call (see "Phase 8" above).
- Running `evaluation/run_experiment.py`'s live benchmark to completion (see
  "Phase 9" above) — this is the one concrete remaining item from the user's
  "run the actual experiments/evaluation" instruction.

Not a code defect — an external account quota, consistent with the same
free-tier limit already documented for Phase 4/5/7. Everything that does NOT
require a live Groq call (all unit/deterministic tests across every phase,
including every new Phase 8/9 test) passes. Real, non-LLM live verification
against `production/` (fault injection, recovery execution, kill switch) was
completed successfully in this session and does not depend on Groq quota at
all — see "Phase 8" above.
