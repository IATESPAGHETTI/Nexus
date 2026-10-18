# Held-out experiment, PARTIAL (2026-10-18): Gemini free tier, 52 valid runs

**Read this first.** This is an incomplete, single-provider result. It is NOT comparable with `EVALUATION_RESULTS_2026-10-16.md` (DeepSeek, different scenarios).

## What happened
- Scenarios: the 8 held-out faults (5 reworded, 3 two-fault) + a reworded healthy control (`fault_injection/scenarios.py::HOLDOUT_*`), prompts/triage/scorer frozen at the commit named below.
- Provider: Gemini `gemini-3.5-flash-lite`, free tier. It allows **15 requests per minute and 500 per day per model**. A first attempt crashed on the per-minute limit; the runner
  was then made rate-limit-aware (retries, pacing, invalid runs excluded). The second attempt hit the **daily** cap after about 52 runs; the 13 runs after that produced no model
  output and were removed (raw file kept). Nothing here was estimated or filled in.
- Done: 52 valid runs over 5 arms (single-agent baseline, hub, hub without critic, blackboard, pipeline), about one run per scenario per arm (two for some).
  **Not done**: `hub_analysis_tools`, `hub_crewai_both`, and the second repeat of most cells. To finish: on a day the quota has reset, run
  `NEXUS_LLM_PROVIDER=gemini NEXUS_LLM_MODEL=gemini-3.5-flash-lite .venv-orchestrator/Scripts/python evaluation/run_matrix.py --set holdout --repeats 2 --pace 50 --resume <this run's .jsonl>`
  (about 700 requests, so it needs two days' quota, or a paid tier).

## How to read the numbers
- Each cell is 1 or 2 runs. **Nothing here is statistically meaningful**; it shows where to look, not what is true.
- The single-agent baseline got every held-out case right including the healthy control (11/11), at about a seventh of the tokens. The multi-agent arms scored 56-70% on this
  provider and these scenarios. Do not generalise: other models behave differently.
- **Correction (same day):** an earlier version of this page said all four multi-agent arms named a cause on the healthy control. That was a SCORING error, not a system error:
  their hypotheses said the shop was "operating normally" (and the Critic agreed), but the scorer read the words "database" and "latency" as a slow-database diagnosis. The scorer now
  recognises "nothing is wrong" statements, and every stored run was re-scored with it: the healthy control is 100% for all arms (1 run each).
- Two-fault scenarios accept either injected cause as correct (`"a|b"` truth).

## Generated report
Code version: `6d3b4ea` (prompts, triage rules and scorer are as of this commit).
Runtime: `gemini/gemini-3.5-flash-lite`. Scenarios: HO-healthy-control, HO-reworded-bad-deployment, HO-reworded-config-error, HO-reworded-db-slowdown, HO-reworded-dependency-failure, HO-reworded-resource-exhaustion, HO-two-faults-db-dependency, HO-two-faults-deploy-db, HO-two-faults-resource-dependency. Repeats per scenario/arm: 2.
Cost is an ESTIMATE: tokens x list price (in $0.3/M, out $1.2/M; deepseek-flash peak price, an assumption because deepseek-chat is not on the pricing page).

## Per-arm results

| Arm | Runs (invalid) | Accuracy | False dx | Abstain | Control OK | Time s (mean±sd) | Tokens (mean±sd) | Calls | Est $/run |
|---|---|---|---|---|---|---|---|---|---|
| baseline_single_agent | 11 (0) | 100% | 0% | 0% | 100% | 1.9±0.6 | 2932±111 | 1.0 | 0.0009 |
| hub_default | 11 (0) | 70% | 0% | 10% | 100% | 10.9±2.6 | 19666±11379 | 8.5 | 0.0065 |
| hub_no_critic | 10 (0) | 56% | 0% | 0% | 100% | 8.5±1.0 | 17457±7958 | 7.5 | 0.0057 |
| blackboard | 10 (0) | 56% | 11% | 0% | 100% | 10.3±1.3 | 20842±11141 | 8.2 | 0.0068 |
| pipeline | 10 (0) | 56% | 0% | 0% | 100% | 16.9±9.6 | 20857±10966 | 8.3 | 0.0068 |

## Comparisons the arms answer

- **baseline_single_agent**: one model call over a flat evidence snapshot, no tools, no critic -> pattern: single agent vs multi-agent
- **hub_default**: hub-and-spoke, default prompts, ADK critic (the shipped system) -> reference
- **hub_no_critic**: hub-and-spoke, critic skipped (ablation) -> pattern: reflection/critic
- **blackboard**: shared blackboard topology, default prompts -> messaging: hub-and-spoke vs blackboard
- **pipeline**: sequential hand-off over the board: Metrics first, the others told what it found -> messaging: hub vs blackboard vs pipeline (hand-off)

## Repeatability (same scenario, repeated)

- baseline_single_agent: 1.0 (2 scenarios repeated)
- hub_default: 0.5 (2 scenarios repeated)
- hub_no_critic: 1.0 (1 scenarios repeated)
- blackboard: 1.0 (1 scenarios repeated)
- pipeline: 1.0 (1 scenarios repeated)

## Per-scenario outcomes (correct runs / runs)

| Scenario | baseline_single_agent | hub_default | hub_no_critic | blackboard | pipeline |
|---|---|---|---|---|---|
| HO-healthy-control | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| HO-reworded-bad-deployment | 2/2 | 2/2 | 1/1 | 1/1 | 1/1 |
| HO-reworded-config-error | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| HO-reworded-db-slowdown | 2/2 | 1/2 | 0/2 | 0/2 | 0/2 |
| HO-reworded-dependency-failure | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| HO-reworded-resource-exhaustion | 1/1 | 0/1 | 0/1 | 0/1 | 1/1 |
| HO-two-faults-db-dependency | 1/1 | 1/1 | 1/1 | 1/1 | 1/1 |
| HO-two-faults-deploy-db | 1/1 | 0/1 | 0/1 | 0/1 | 0/1 |
| HO-two-faults-resource-dependency | 1/1 | 1/1 | 1/1 | 1/1 | 0/1 |

## Caveats

- Small sample: with few repeats per scenario a difference of one run is within noise; do not read rankings as significant.
- Prompts, guardrail logic and the Critic were tuned earlier on these same five scenarios; held-out scenarios are needed before claiming accuracy.
- Scenario text given to the agents is symptom-only (fault_injection/scenarios.py `blind_symptom`); the ground truth is read only for scoring.
- Triage chooses which specialists are called from the symptom text, so arms call different numbers of agents.
- Recovery calls are excluded from every arm (trigger_recovery=False), so token totals cover diagnosis only.
- Latency includes provider rate-limit retries and shared-machine noise.
- Runs whose agents reported errors (for example provider rate limits) were retried; runs still failing are listed as invalid and excluded from accuracy.
