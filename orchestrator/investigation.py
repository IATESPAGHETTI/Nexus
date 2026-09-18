"""Phase 6: bounded evidence -> hypothesis -> critic re-evaluation loop.

```
Incident description
   |
Incident Manager dispatch (Phase 5 incident_manager.investigate_incident,
   real A2A fan-out to the 4 diagnostic agents)
   |
Findings (real Finding objects, each with real MCP evidence)
   |
Evidence Agent (real A2A call -- agents/evidence/a2a_service.py) -> Hypotheses
   |
Root-Cause Critic (real A2A call -- agents/critic/a2a_service.py), bounded loop
(MAX_REEVALUATION_LOOPS iterations, never infinite -- root CLAUDE.md section 14):
   SUPPORTED                                  -> diagnosis reached, stop
   CONTRADICTED                               -> reject hypothesis, try the next one
   INSUFFICIENT_EVIDENCE / REQUEST_MORE_EVIDENCE
                                               -> real second-round A2A dispatch to
                                                  the diagnostic agents for more
                                                  evidence, hypotheses regenerated,
                                                  loop continues (if budget remains)
   ABSTAIN                                    -> abstain, stop
   loop exhausted without SUPPORTED/ABSTAIN   -> abstain (never force a diagnosis)
```

Every transition is persisted to the backend event store and running incident
state via `orchestrator/event_bridge.py` (real HTTP calls to `backend/`).
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import event_bridge  # noqa: E402
from incident_manager import DIAGNOSTIC_AGENTS, investigate_incident  # noqa: E402
from remote_call import call_remote_agent  # noqa: E402

MAX_REEVALUATION_LOOPS = int(os.environ.get("MAX_REEVALUATION_LOOPS", "3"))

EVIDENCE_AGENT_NAME = "evidence_agent"
EVIDENCE_AGENT_DESCRIPTION = "NEXUS Evidence Agent: synthesizes diagnostic Findings into Hypotheses."
CRITIC_AGENT_NAME = "root_cause_critic"
CRITIC_AGENT_DESCRIPTION = "NEXUS Root-Cause Critic: independently challenges the leading Hypothesis."

_OPEN_STATUSES = ("PROPOSED", "UNDER_REVIEW", "NEEDS_EVIDENCE")


def _flatten_evidence(findings_by_agent: dict) -> list[dict]:
    pool: list[dict] = []
    for finding in findings_by_agent.values():
        pool.extend(finding.get("evidence", []) or [])
    return pool


def _leading_hypothesis(hypotheses: list[dict]) -> dict | None:
    open_ones = [h for h in hypotheses if h.get("status") in _OPEN_STATUSES]
    if not open_ones:
        return None
    return max(open_ones, key=lambda h: h.get("confidence", 0.0))


async def _dispatch_diagnostic_agents(incident_id: str, question: str, agent_names: list[str]) -> dict:
    for name in agent_names:
        event_bridge.emit_event(incident_id, "AGENT_STARTED", source="incident_manager", target=name)

    result = await investigate_incident(question, agent_names=agent_names)

    for name in result["agents_responded"]:
        finding = result["findings"][name]
        a2a_meta = result["a2a"].get(name, {})
        event_bridge.emit_event(
            incident_id,
            "A2A_MESSAGE_SENT",
            source="incident_manager",
            target=name,
            status="completed",
            payload={"task_id": a2a_meta.get("task_id"), "context_id": a2a_meta.get("context_id")},
        )
        # mcp/audit.py bridge: these are the same real tool/arguments/result
        # facts recorded locally inside this agent's own MCP server process --
        # see orchestrator/event_bridge.py's module docstring.
        for item in finding.get("evidence", []) or []:
            ok = item["result"].get("ok") if isinstance(item.get("result"), dict) else None
            event_bridge.emit_event(
                incident_id,
                "MCP_TOOL_CALL",
                source=name,
                status="ok" if ok else "unknown",
                payload={"tool": item["tool"], "arguments": item["arguments"], "evidence_id": item["evidence_id"]},
            )
            event_bridge.emit_event(
                incident_id,
                "MCP_TOOL_RESULT",
                source=name,
                payload={"evidence_id": item["evidence_id"], "tool": item["tool"]},
            )
        event_bridge.emit_event(
            incident_id,
            "AGENT_COMPLETED",
            source=name,
            payload={"finding_id": finding["finding_id"], "confidence": finding["confidence"]},
        )
        event_bridge.emit_event(
            incident_id,
            "EVIDENCE_FOUND",
            source=name,
            payload={
                "finding_id": finding["finding_id"],
                "evidence_ids": [e["evidence_id"] for e in finding.get("evidence", []) or []],
            },
        )

    for name in set(agent_names) - set(result["agents_responded"]):
        event_bridge.emit_event(
            incident_id,
            "AGENT_COMPLETED",
            source=name,
            status="failed",
            payload={"reason": "no A2A response (Groq rate limit or agent unavailable)"},
        )

    return result


async def _call_evidence_agent(incident_id: str, findings_by_agent: dict) -> list[dict]:
    call = await call_remote_agent(EVIDENCE_AGENT_NAME, EVIDENCE_AGENT_DESCRIPTION, json.dumps(findings_by_agent))
    event_bridge.emit_event(
        incident_id,
        "A2A_MESSAGE_SENT",
        source="incident_manager",
        target=EVIDENCE_AGENT_NAME,
        status="completed",
        payload={"task_id": call["task_id"], "context_id": call["context_id"]},
    )
    response = call["response"] if isinstance(call["response"], dict) else {}
    hypotheses = response.get("hypotheses", [])
    if not isinstance(hypotheses, list):
        hypotheses = []
    for hypothesis in hypotheses:
        event_bridge.emit_event(incident_id, "HYPOTHESIS_CREATED", source=EVIDENCE_AGENT_NAME, payload=hypothesis)
    return hypotheses


async def _call_critic(incident_id: str, hypothesis: dict, evidence_pool: list[dict]) -> dict:
    payload = {"hypothesis": hypothesis, "evidence_pool": evidence_pool}
    call = await call_remote_agent(CRITIC_AGENT_NAME, CRITIC_AGENT_DESCRIPTION, json.dumps(payload))
    event_bridge.emit_event(
        incident_id,
        "A2A_MESSAGE_SENT",
        source="incident_manager",
        target=CRITIC_AGENT_NAME,
        status="completed",
        payload={"task_id": call["task_id"], "context_id": call["context_id"]},
    )
    critique = call["response"] if isinstance(call["response"], dict) else None
    if not critique:
        critique = {
            "critique_id": None,
            "hypothesis_id": hypothesis.get("hypothesis_id"),
            "verdict": "INSUFFICIENT_EVIDENCE",
            "rationale": "critic A2A call returned no parseable response",
        }
    event_bridge.emit_event(
        incident_id, "CRITIC_CHALLENGE", source=CRITIC_AGENT_NAME, target=hypothesis.get("hypothesis_id"), payload=critique
    )
    return critique


async def run_investigation(
    incident_description: str,
    agent_names: list[str] | None = None,
    max_loops: int | None = None,
) -> dict:
    """Runs the full Phase 6 investigation and returns the final persisted
    incident state (fetched back from the backend, not an in-memory copy)."""
    max_loops = MAX_REEVALUATION_LOOPS if max_loops is None else max_loops
    agent_names = agent_names or list(DIAGNOSTIC_AGENTS)

    incident_id = event_bridge.create_incident(incident_description)
    event_bridge.emit_event(
        incident_id, "INCIDENT_CREATED", source="incident_manager", payload={"description": incident_description}
    )

    dispatch = await _dispatch_diagnostic_agents(incident_id, incident_description, agent_names)
    findings_by_agent = dispatch["findings"]
    event_bridge.update_state(incident_id, agent_findings=findings_by_agent, agent_messages=dispatch["a2a"])

    hypotheses = await _call_evidence_agent(incident_id, findings_by_agent)
    event_bridge.update_state(incident_id, hypotheses=hypotheses)

    decision = None
    reason = None
    critic_results: list[dict] = []
    loops_used = 0

    for loop_index in range(1, max_loops + 1):
        loops_used = loop_index
        leading = _leading_hypothesis(hypotheses)
        if leading is None:
            decision, reason = "ABSTAINED", "no open hypothesis left to evaluate"
            break

        event_bridge.emit_event(
            incident_id,
            "RE_EVALUATION_STARTED",
            source="root_cause_critic",
            target=leading["hypothesis_id"],
            payload={"loop": loop_index, "max_loops": max_loops},
        )
        evidence_pool = _flatten_evidence(findings_by_agent)
        critique = await _call_critic(incident_id, leading, evidence_pool)
        critic_results.append(critique)
        verdict = critique.get("verdict", "INSUFFICIENT_EVIDENCE")

        if verdict == "SUPPORTED":
            leading["status"] = "SUPPORTED"
            event_bridge.emit_event(incident_id, "HYPOTHESIS_UPDATED", source=EVIDENCE_AGENT_NAME, payload=leading)
            decision = "DIAGNOSED"
            reason = f"hypothesis {leading['hypothesis_id']} SUPPORTED by root-cause critic"
            event_bridge.emit_event(
                incident_id, "DIAGNOSIS_REACHED", source="root_cause_critic", payload={"hypothesis": leading, "critique": critique}
            )
            break

        if verdict == "CONTRADICTED":
            leading["status"] = "REJECTED"
            event_bridge.emit_event(incident_id, "HYPOTHESIS_UPDATED", source=EVIDENCE_AGENT_NAME, payload=leading)
            event_bridge.update_state(incident_id, hypotheses=hypotheses, critic_results=critic_results)
            continue  # try the next-leading open hypothesis within the same loop budget

        if verdict == "ABSTAIN":
            leading["status"] = "ABSTAINED"
            event_bridge.emit_event(incident_id, "HYPOTHESIS_UPDATED", source=EVIDENCE_AGENT_NAME, payload=leading)
            decision = "ABSTAINED"
            reason = critique.get("rationale", "root-cause critic abstained")
            break

        # INSUFFICIENT_EVIDENCE / REQUEST_MORE_EVIDENCE (or any unrecognized verdict,
        # which agents/critic/agent.py already normalizes down to this bucket).
        leading["status"] = "NEEDS_EVIDENCE"
        event_bridge.emit_event(incident_id, "HYPOTHESIS_UPDATED", source=EVIDENCE_AGENT_NAME, payload=leading)
        event_bridge.emit_event(
            incident_id,
            "EVIDENCE_REQUESTED",
            source="root_cause_critic",
            target="incident_manager",
            payload={"requested_evidence": critique.get("requested_evidence", []), "hypothesis_id": leading["hypothesis_id"]},
        )

        if loop_index == max_loops:
            break  # no budget left to re-dispatch; falls through to the abstain path below

        follow_up = (
            f"Re-investigate incident: {incident_description}. The root-cause critic "
            f"requested more evidence for hypothesis '{leading['statement']}': "
            f"{critique.get('requested_evidence', [])}. Missing evidence noted: "
            f"{leading.get('missing_evidence', [])}."
        )
        more = await _dispatch_diagnostic_agents(incident_id, follow_up, agent_names)
        for name, finding in more["findings"].items():
            findings_by_agent[name] = finding  # latest finding per agent supersedes the prior one
        event_bridge.update_state(incident_id, agent_findings=findings_by_agent)

        hypotheses = await _call_evidence_agent(incident_id, findings_by_agent)
        event_bridge.update_state(incident_id, hypotheses=hypotheses, critic_results=critic_results)

    if decision is None:
        decision = "ABSTAINED"
        reason = f"reached MAX_REEVALUATION_LOOPS ({max_loops}) without a supported diagnosis"

    if decision == "ABSTAINED":
        event_bridge.emit_event(
            incident_id, "ABSTENTION", source="incident_manager", payload={"reason": reason, "loops_used": loops_used}
        )

    event_bridge.update_state(
        incident_id,
        status=decision,
        hypotheses=hypotheses,
        critic_results=critic_results,
        decision={"outcome": decision, "reason": reason, "loops_used": loops_used, "max_loops": max_loops},
    )
    event_bridge.emit_event(incident_id, "INCIDENT_STATUS_CHANGED", source="incident_manager", payload={"status": decision})

    return event_bridge.get_incident(incident_id)
