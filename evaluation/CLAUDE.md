# Evaluation Local Instructions

## Purpose
Evaluation pipeline: runs blind fault-injection scenarios from
`fault_injection/` against NEXUS and 2 comparison arms, scores results
against ground truth, reports the metrics `docs/EVALUATION.md` names.

## Owned
- `production_reader.py` — bounded read-only HTTP client to `production/`,
  used ONLY by the single-agent baseline. One flat snapshot
  (`/metrics`+`/logs`+`/changes`+`/db/diagnostics`), not iterative tool
  access — this is what makes the baseline "single-agent, no tool loop."
- `baselines.py` — `single_agent_baseline(incident_description)`: ONE real
  Groq/GPT-OSS-120B `litellm.completion` call (no ADK agent, no tools, no
  multi-agent coordination, no critic) given one evidence snapshot, asked to
  pick a root cause from the same closed vocabulary as
  `production/state.FAULT_TYPES`. `build_result()` is the structural
  enforcement (mirrors every other `build_*` in this system) — an
  out-of-catalog `root_cause` is normalized to `"unknown"`, never trusted.
- `scoring.py` — pure functions, no network: `classify_statement()` maps a
  NEXUS Hypothesis's free-text statement onto the closed root-cause
  vocabulary via keyword matching (for scoring only, never fed back into any
  agent); `score_run()`/`aggregate()` compute root-cause accuracy, false
  diagnosis rate, abstention rate, diagnosis rate, avg latency — comparing
  two already-known strings after the fact, never importing
  `fault_injection/scenarios.py` itself (ground truth flows in only as a
  parameter from `run_experiment.py`).
- `run_experiment.py` — the actual benchmark driver. For each scenario:
  inject the real fault -> run all 3 arms (`single_agent_baseline`,
  `orchestrator.investigation.run_investigation` with
  `trigger_recovery=False`, and the same with `skip_critic=True` for the
  no-critic ablation) -> clear the fault -> score. Writes a JSON report to
  `evaluation/results/<timestamp>.json` (gitignored) and prints the
  aggregate table. Real, not simulated — every arm makes real Groq calls
  against the real live stack.

## The 3 comparison arms (docs/EVALUATION.md)
```text
1. single_agent_baseline  -- evaluation/baselines.py, one LLM call, no tools
2. full_nexus             -- orchestrator/investigation.py, full pipeline,
                              trigger_recovery=False (root-cause scoring only,
                              not a recovery-effectiveness benchmark)
3. nexus_no_critic        -- same, skip_critic=True: zero real A2A calls to
                              root_cause_critic, a genuine ablation
```

## Rules
Owns ground truth (via `fault_injection.scenarios.get_ground_truth`,
imported only in `run_experiment.py`) — must never leak it into `agents/` or
`orchestrator/`. Never fabricate a metric: `run_experiment.py` reports
whatever the real runs actually produced, including abstentions, Groq
rate-limit failures, and unclassifiable hypothesis statements (scored as
`"unknown"`, not silently dropped from the aggregate).

## Dependency isolation
No dedicated `.venv-evaluation/` — `litellm`/`python-dotenv`/`httpx` are
already pinned identically in `orchestrator/requirements.txt`; runs inside
`.venv-orchestrator/` (see `evaluation/requirements.txt`'s own note).

## Status
Phase 9: **implemented + unit-tested** (`evaluation/tests/test_scoring.py`,
11 fast pure tests, no network — `scoring.py`'s classification/aggregation
logic and `baselines.build_result`'s structural enforcement). The full live
`run_experiment.py` benchmark across all 5 scenarios has **not yet been run
to completion** — blocked by the Groq account's daily token quota (TPD
200000) being exhausted during this same Phase 8/9 session's live
verification (see `docs/PROJECT_STATE.md` "Blockers"), the same external
account limit already documented for Phase 7. Not run != broken: every unit
that doesn't need a live Groq call is tested and passing.

## Test
```bash
.venv-orchestrator/Scripts/python -m pytest evaluation/tests -q   # fast, no network
# Live benchmark (needs the entire stack running + the configured provider's API key):
.venv-orchestrator/Scripts/python evaluation/run_experiment.py
```

## Provider configuration
DeepSeek `deepseek-chat` is now the default and official NEXUS production/
benchmark configuration. Groq `openai/gpt-oss-120b` and Gemini
`gemini-2.5-flash` remain supported as opt-in overrides via
`NEXUS_LLM_PROVIDER`/`NEXUS_LLM_MODEL` in `.env` (with their respective
`GROQ_API_KEY`/`GEMINI_API_KEY`). The runner labels any non-DeepSeek runtime
`development_validation_not_official_nexus_benchmark`. Never place a key in
source or documentation.

## Usually inspect
`run_experiment.py`, `scoring.py`, `baselines.py`, `fault_injection/scenarios.py`,
`orchestrator/investigation.py`, `docs/EVALUATION.md`

## Usually don't touch
`agents/`, `guardrails/` (must never import this package or `fault_injection/`)
