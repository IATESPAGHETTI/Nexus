# NEXUS Phase 10 Plan — Integration, Demo, Docs, Final Verification

Root `CLAUDE.md` names Phase 10 "Evaluation" and Phase 11 "Integration + Demo".
The user's Phase 10 instruction for this session is broader and supersedes
that split for now: it bundles system integration, a reproducible demo,
academic packaging, and final cleanup into one sequential Phase 10 with four
subphases (10A-10D). This file tracks that work only; `docs/PROJECT_STATE.md`
remains the canonical durable project memory.

Hard constraints carried into every subphase (per explicit user instruction):
- Preserve Phases 1-9 exactly; no unnecessary rewrites.
- No fabricated events, metrics, benchmark results, recovery outcomes, or
  team contributions (Mukund/Vanshika get credit only for verified work).
- Phase 9's official live benchmark is NOT complete until it is actually run
  — do not claim otherwise anywhere in Phase 10 output.
- Groq daily quota status is unknown/assumed still constrained and Gemini
  quota is exhausted — **no live Groq or Gemini calls this session.** Use
  deterministic/mocked paths. If a real-LLM step is genuinely required for a
  subphase, stop and document the gap rather than spending quota.
- Update this file and `docs/PROJECT_STATE.md` after each completed subphase.

## 10A — Full-System Integration
Goal: confirm the large uncommitted Phase 7/8/9 changeset (dashboard, guardrails,
recovery, fault injection, evaluation) still integrates as one coherent system,
using only deterministic/non-LLM verification (no quota spend).

Status: **DONE** (2026-09-18)

Results:
- [x] Full deterministic regression sweep, all green:
      backend/production (`.venv`) 29/29;
      MCP (`.venv-mcp`, production running on :8001) 22/22;
      fast agents (`.venv-agents`: finding/evidence-critic/recovery) 27/27;
      fast orchestrator+guardrails (`.venv-orchestrator`) 27/27;
      fault_injection (`.venv`, live prod, 5 unit + 2 real-HTTP) 7/7;
      evaluation (`.venv-orchestrator`, pure) 14/14.
      Total: 126/126 deterministic tests passing, zero Groq/Gemini calls made.
- [x] `docker compose config --quiet` — passes cleanly.
- [x] Dashboard `npm install` + `npm run build` — **now succeeds** (475
      modules, builds in ~3s). The prior session's blocker (`npm` launcher
      missing `npm-cli.js`) is no longer present in this environment/session;
      not a NEXUS code issue, was always external tooling.
- [x] `git diff --check` — clean (0 conflict markers; only expected
      LF-will-become-CRLF advisories on Windows, not a real problem).
- [x] Secret scan (diff + working tree, `gsk_`/`AIza` patterns) — no real
      secrets found; only the documented placeholder in `.env.example`.
      `.env.example`/`.gitignore` diffs reviewed line-by-line: only the new
      opt-in Gemini placeholder vars and 2 new gitignore entries
      (`guardrails/.kill_switch`, `evaluation/results/`) — no secret material.

**Real bug found and fixed during this pass (in scope — a genuine
full-system-integration defect, not a rewrite):**
`production/service.py`'s `resource_exhaustion` fault applied its random
500/latency degradation to **every** endpoint, including `/admin/*` — the
fault-injection/recovery control plane itself. This meant
`POST /admin/recovery/scale_resources` (the real recovery action for that
exact fault) could randomly fail with a fake `ResourceExhaustedError`, purely
because of the fault it was trying to clear — a genuine reliability gap for
Phase 8/9, not a test-only issue. Reproduced directly:
`tests/test_fault_recovery.py` failed on a different random test each of
several full-file runs before the fix (0/5 clean runs), all green after
(5/5 clean runs). Fix: middleware now skips the resource_exhaustion
degradation for any `/admin`-prefixed path, since that path is NEXUS's own
control plane, not simulated customer traffic — customer-facing endpoints
(`/orders`, `/metrics`, etc.) still degrade exactly as before, preserving the
diagnostic signal the Metrics Agent relies on. Full regression re-run clean
afterward (backend/production 29/29, fault_injection 7/7).

Drift vs. `docs/PROJECT_STATE.md`: none material. The file's own
"Continuation check — 2026-09-18" entry already matched the working tree
exactly; the one new fact this pass adds is the `/admin` fault-isolation fix
above and the now-working dashboard build.

## 10B — Reproducible End-to-End Demo
Goal: a documented, repeatable procedure (script and/or README walkthrough)
that starts NEXUS, injects a fault, and shows the full investigation flow
through to diagnosis/abstention and recovery — reproducible by a third party
without live-running it in this session unless quota/time allow a real pass.

Status: **DONE** (2026-09-18), with one step honestly flagged as pending live
confirmation.

Delivered:
- `orchestrator/run_demo.py` (new) — thin CLI wrapper around the existing,
  already-tested `run_investigation()` (same function
  `orchestrator/tests/test_investigation_e2e.py` exercises). Not a new
  orchestration path. Verified this session: imports cleanly, `--help`
  parses correctly, zero Groq calls made by that verification.
- `docs/DEMO_RUNBOOK.md` (new) — the full 7-step reproducible procedure
  (start production+backend -> start all 7 A2A services -> inject fault ->
  run investigation -> watch dashboard -> approve recovery -> teardown).
- **Live-verified this session (real processes, zero LLM calls):** started
  the entire non-LLM stack — `production` (8001), `backend` (8000), and all
  7 A2A services (8101-8107) as 9 genuinely separate OS processes — confirmed
  every one of the 7 real Agent Cards returns HTTP 200. Injected a real
  `bad_deployment` fault via `POST /admin/fault/inject`, confirmed
  `/admin/state` reflected it, created a real incident via
  `POST /incidents` on the live backend (`INC-5f0213ea`), then cleared the
  fault and cleanly stopped all 9 processes (`netstat` confirmed every port
  free afterward).
- **Honestly NOT run this session:** runbook step 4
  (`orchestrator/run_demo.py` actually invoking `run_investigation()`) needs
  real Groq calls to every diagnostic agent + Evidence Agent + Critic (+
  Recovery Agent on a DIAGNOSED path) — per this session's explicit
  instruction not to spend Groq/Gemini quota, this exact step was not
  executed. Flagged in `docs/DEMO_RUNBOOK.md` itself, not silently skipped.

## 10C — Documentation & Academic Packaging
Goal: bring root `README.md`, `docs/ARCHITECTURE.md`, and related docs in line
with the actual Phase 1-9 implementation for submission, without inventing
capabilities or contributions.

Status: **DONE** (2026-09-18)

Delivered:
- `README.md` — rewritten from a Phase-1-only quickstart to reflect the real
  current system: what NEXUS actually does end to end, honest development
  ownership (Deepu; Mukund/Vanshika as listed academic team members only,
  per root `CLAUDE.md` section 4 — no fabricated contributions), the real
  runtime LLM (Groq GPT-OSS 120B, official; Gemini opt-in dev-only), a
  status-at-a-glance section naming the one real gap (Phase 9's live
  benchmark), per-component test commands, dashboard instructions, and a
  link to the new `docs/DEMO_RUNBOOK.md`.
- `docs/ARCHITECTURE.md` — its "Status" section was stale (said "Phase 5...
  evidence/critic/recovery/guardrails/dashboard/evaluation remain target
  architecture — not yet built", which was no longer true as of Phase 9).
  Corrected to state plainly that Phases 1-9 are implemented, name the one
  real remaining gap (Phase 9 live benchmark), and point to
  `docs/PROJECT_STATE.md`/`NEXUS_PHASE10_PLAN.md` as the live sources of
  truth rather than duplicating their detail here.
- `docs/API_CONTRACT.md`, `docs/EVENT_SCHEMA.md`, `docs/EVALUATION.md`: left
  unchanged this pass — spot-checked against the Phase 6/8/9 sections of
  `docs/PROJECT_STATE.md` and found already current (each was updated
  in-phase, per the "Completed" log), so no drift to fix.

## 10D — Final Verification & Cleanup
Goal: final regression pass, process/port cleanup, secret scan, and a closing
`docs/PROJECT_STATE.md` update reflecting true end-of-project state.

Status: **DONE** (2026-09-18)

Results:
- Full deterministic regression re-run one final time after every 10A-10C
  change (including the `production/service.py` fault-isolation fix):
  root pytest 29/29, fault_injection 7/7, MCP 22/22, fast agents 27/27, fast
  orchestrator+guardrails 27/27, evaluation 14/14 — **126/126**, unchanged
  from the 10A count (10B/10C added no Python test-affecting code beyond the
  new, separately-verified `orchestrator/run_demo.py` CLI wrapper).
- Removed `env.txt`: a stray, empty (0 bytes), untracked file with zero
  references anywhere in the repo (confirmed by search) — safe cleanup, not
  a functional change.
- Process/port cleanup: every server started during this session's 10A/10B
  live verification (production, backend, all 7 A2A services — 9 processes
  across two separate live-verification passes) was stopped; `netstat`
  confirmed ports 8000/8001/8101-8107 free after each pass and again at the
  end of 10D. `guardrails/.kill_switch` sentinel confirmed absent (never
  engaged this session).
- Secret scan (diff + full working tree, `gsk_`/`AIza`/generic
  `api_key=...`-literal patterns) — clean; only the documented placeholder in
  `.env.example`.
- `git status --short` end state: the same Phase 1-9 changeset as this
  session's start, plus this session's real Phase 10 additions
  (`NEXUS_PHASE10_PLAN.md`, `docs/DEMO_RUNBOOK.md`, `orchestrator/run_demo.py`,
  `README.md`/`docs/ARCHITECTURE.md`/`docs/PROJECT_STATE.md` updates, the
  `production/service.py` fix, `env.txt` removed) — nothing unexpected, no
  accidental reverts. **Nothing was committed** — per root `CLAUDE.md`
  section 28 and this session's own operating rules, commits happen only on
  explicit user request, which was not given.

## Phase 10 summary
10A-10D all complete for what can honestly be verified without spending
Groq/Gemini quota. The two concrete items still pending a live LLM call, both
flagged (not silently skipped or faked), are:
1. `docs/DEMO_RUNBOOK.md` step 4 — the actual `orchestrator/run_demo.py`
   investigation run.
2. Phase 9's official 3-arm benchmark (`evaluation/run_experiment.py`) across
   all 5 fault scenarios.
Both are unblocked purely by Groq quota, not by any missing code — see
`docs/PROJECT_STATE.md` "Blockers" for the exact resume point.
