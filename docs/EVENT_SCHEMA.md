# NEXUS Event Schema

Live event contract. Every major transition in the system emits one of these events.
The dashboard subscribes to the event stream and must never fabricate or replay events
that didn't actually happen.

## Envelope

```json
{
  "event_id": "evt-123",
  "incident_id": "INC-001",
  "timestamp": "2026-01-01T12:00:00Z",
  "event_type": "AGENT_HANDOFF",
  "source": "evidence_agent",
  "target": "root_cause_critic",
  "status": "started",
  "payload": { "message": "Review hypothesis H1" }
}
```

- `event_id`: unique, monotonically orderable within an incident.
- `incident_id`: foreign key into incident state.
- `timestamp`: ISO 8601 UTC.
- `event_type`: one of the minimum set below (extend, never repurpose).
- `source` / `target`: component or agent name; `target` optional for non-directed events.
- `status`: free-form short status (`started`, `completed`, `failed`, ...) where applicable.
- `payload`: event-specific structured data. No private model chain-of-thought — only
  auditable artifacts (observation, evidence, hypothesis, supporting/contradicting
  evidence, requested evidence, decision).

## Minimum event types

```text
INCIDENT_CREATED
INCIDENT_STATUS_CHANGED
AGENT_STARTED
AGENT_COMPLETED
A2A_MESSAGE_SENT
MCP_TOOL_CALL
MCP_TOOL_RESULT
EVIDENCE_FOUND
HYPOTHESIS_CREATED
HYPOTHESIS_UPDATED
CRITIC_CHALLENGE
EVIDENCE_REQUESTED
RE_EVALUATION_STARTED
DIAGNOSIS_REACHED
ABSTENTION
RECOVERY_PLAN_CREATED
SAFETY_CHECK
HUMAN_APPROVAL_REQUIRED
HUMAN_APPROVED
RECOVERY_STARTED
RECOVERY_COMPLETED
VERIFICATION_STARTED
VERIFICATION_COMPLETED
INCIDENT_RESOLVED
```

## Status

Implemented (Phase 6). Producer: `orchestrator/event_bridge.py` (real HTTP POST
to `backend/`), called throughout `orchestrator/investigation.py`'s bounded
re-evaluation loop. Consumer/store: `backend/app/incident_store.py` +
`backend/app/main.py`'s `/incidents/{id}/events` endpoints. Event types
actually emitted so far: `INCIDENT_CREATED`, `AGENT_STARTED`,
`A2A_MESSAGE_SENT`, `MCP_TOOL_CALL`, `MCP_TOOL_RESULT`, `AGENT_COMPLETED`,
`EVIDENCE_FOUND`, `HYPOTHESIS_CREATED`, `HYPOTHESIS_UPDATED`,
`RE_EVALUATION_STARTED`, `CRITIC_CHALLENGE`, `EVIDENCE_REQUESTED`,
`DIAGNOSIS_REACHED`, `ABSTENTION`, `INCIDENT_STATUS_CHANGED`. Not yet emitted:
the recovery/approval/verification event types (`RECOVERY_*`, `SAFETY_CHECK`,
`HUMAN_APPROVAL_*`, `VERIFICATION_*`, `INCIDENT_RESOLVED`) — no producer exists
for them yet (Phase 8, recovery). `MCP_TOOL_CALL`/`MCP_TOOL_RESULT` are
sourced from the real evidence already present in each diagnostic agent's
Finding, not a direct read of `mcp/audit.py`'s in-process deque — see
`orchestrator/event_bridge.py`'s module docstring for why, and
`docs/PROJECT_STATE.md`'s "Known limitations" for this documented as an
explicit scope boundary, not an oversight. `dashboard/` has no consumer yet
(Phase 7).
