# Fault Injection Local Instructions

## Purpose
Benchmark/fault scenarios injected into `production/` for blind evaluation.
Vanshika's workstream (implemented by Deepu).

## Contract
Each scenario must map to one of the minimum failure classes in `docs/EVALUATION.md`
(bad deployment, database slowdown, configuration error, dependency failure, resource
exhaustion) and carry a ground-truth label used only by `evaluation/`, never exposed
to diagnostic agents.

## Rules
Do not hard-code the diagnosis into agent logic elsewhere in the repo. Ground truth
lives here and in `evaluation/` only.

## Status
Not yet implemented (Phase 10 in the build order).
