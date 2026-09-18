# Evaluation Local Instructions

## Purpose
Evaluation pipeline: runs blind fault-injection scenarios from `fault_injection/`
against NEXUS (and baselines), scores results against ground truth, reports metrics
from `docs/EVALUATION.md`.

## Rules
Owns ground truth — must never leak it into `agents/` or `orchestrator/`. Do not
manipulate results; report what actually happened, including failures/abstentions.

## Status
Not yet implemented (Phase 10/11 in the build order).
