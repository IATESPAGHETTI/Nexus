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

First complete live benchmark recorded 2026-10-13 (numbers and the three discarded earlier runs are in
`docs/PROJECT_STATE.md`). One run per arm per scenario, so results are directional. NEXUS arms are scored on the
Evidence Agent's structured `fault_class`; every arm gets a full production reset, fault injection and 30 customer
requests first. Token counts are provider-reported; dollar cost and quota are not computed. Run:
`.venv-orchestrator/Scripts/python evaluation/run_experiment.py` (paid: about 15 model-heavy runs).
