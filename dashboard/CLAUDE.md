# Dashboard Local Instructions

## Purpose
Live observability frontend: investigation graph, agent status cards, A2A stream,
MCP activity, timeline, evidence/hypothesis/critic/recovery panels. Vanshika's
workstream (implemented by Deepu). Stack not yet decided (see root CLAUDE.md).

## Rules
No business logic here — this is a pure renderer of `backend/` state and the live
event stream (`docs/EVENT_SCHEMA.md`). Never expose private model chain-of-thought;
only the auditable artifacts (observation, evidence, hypothesis, supporting/
contradicting evidence, requested evidence, decision).

## Status
Not yet implemented (Phase 8 in the build order).
