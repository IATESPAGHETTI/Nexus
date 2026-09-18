# Guardrails Local Instructions

## Purpose
Safety layer for recovery: safety validation, sandbox/controlled validation, human
approval gating, kill switch.

## Contract
Recovery flow: `PROPOSED -> SAFETY VALIDATION -> SANDBOX/CONTROLLED VALIDATION ->
HUMAN APPROVAL -> EXECUTION -> VERIFICATION`. No step may be skipped.

## Rules
No autonomous destructive production action, ever. Recovery must not bypass this
layer under any circumstance, including "the demo needs to finish."

## Status
Not yet implemented (Phase 9 in the build order).

## Test
`pytest guardrails/tests` (create when guardrail logic is implemented).
