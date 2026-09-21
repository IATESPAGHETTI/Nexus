# NEXUS Evaluation

## Purpose

Quantitatively compare NEXUS against simpler baselines using blind fault-injection
scenarios. Ground truth lives here and in `fault_injection/` — it must never leak into
the diagnostic agents (`agents/metrics`, `logs_traces`, `change_analysis`, `database`,
`evidence`, `critic`).

## Failure classes (minimum)

```text
bad deployment
database slowdown
configuration error
dependency failure
resource exhaustion
```

## Comparison arms (Phase 9)

```text
1. Single-agent baseline
2. Full multi-agent NEXUS
3. Ablation without critic/falsification loop
```

Same blind scenarios and evaluation criteria across all arms. No result manipulation.

## Metrics

```text
root-cause accuracy
evidence accuracy
false diagnosis rate
abstention correctness
diagnosis time
remediation success
tool cost
token cost (reported as `Unavailable from provider` unless Groq returns a
provider value; no quota or token number is inferred)
```

## Status

Phase 9's fault scenarios, injector, three-arm benchmark runner, and pure
scoring tests are implemented. The runner executes five controlled scenarios
and writes the raw per-run records plus aggregates to `evaluation/results/`.

The first complete live benchmark has not yet been recorded. It is blocked by
the Groq account's exhausted daily token quota (TPD 200000), not substituted
with synthetic output. When quota headroom is available, start the full stack
and run `.venv-orchestrator/Scripts/python evaluation/run_experiment.py`.
Report the generated JSON as the only source for measured evaluation values.
