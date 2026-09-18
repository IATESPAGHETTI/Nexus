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

## Comparison arms (Phase 11)

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
token cost
```

## Status

Not started (Phase 10/11 in the build order). `fault_injection/` scenarios and this
pipeline depend on Phases 1-9 being functional first.
