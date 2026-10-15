"""Pydantic models for the NEXUS data contracts (docs/API_CONTRACT.md).

One shared module at the repo root (like runtime_config.py). The agent builders
(`agents/common/finding.py`, `agents/evidence`, `agents/critic`, `agents/recovery`)
validate what they produce against these models, so a malformed object fails at
the agent boundary instead of travelling through A2A. The orchestrator builds
the final `IncidentReport` from the stored incident and can render it as JSON or
Markdown.

Models allow extra fields on purpose: the pipeline adds bookkeeping keys later
(`usage`, `revision`, `previous_confidence`, ...) and those must not break validation.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

Verdict = Literal["SUPPORTED", "CONTRADICTED", "INSUFFICIENT_EVIDENCE", "REQUEST_MORE_EVIDENCE", "ABSTAIN"]
HypothesisStatus = Literal[
    "PROPOSED", "UNDER_REVIEW", "CHALLENGED", "NEEDS_EVIDENCE", "SUPPORTED", "REJECTED", "ABSTAINED"
]
RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]


class _Base(BaseModel):
    model_config = ConfigDict(extra="allow")


class EvidenceItem(_Base):
    evidence_id: str
    tool: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    result: Any = None
    timestamp: str


class TimeWindow(_Base):
    start: str
    end: str


class Finding(_Base):
    finding_id: str
    agent: str
    observation: str
    source: str
    window: TimeWindow
    evidence: list[EvidenceItem] = Field(default_factory=list)
    interpretation: str
    confidence: float = Field(ge=0.0, le=1.0)
    limitations: str


class Hypothesis(_Base):
    hypothesis_id: str
    statement: str = Field(min_length=1)
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    missing_evidence: list[str] = Field(default_factory=list)
    requested_next_investigation: Optional[str] = None
    status: HypothesisStatus = "PROPOSED"
    revision: int = 1
    created_at: str


class Critique(_Base):
    critique_id: str
    hypothesis_id: Optional[str] = None
    verdict: Verdict
    contradictions: list[str] = Field(default_factory=list)
    unsupported_assumptions: list[str] = Field(default_factory=list)
    alternative_explanations: list[str] = Field(default_factory=list)
    requested_evidence: list[str] = Field(default_factory=list)
    rationale: str
    evidence_pool_size: int = 0
    timestamp: str


class RecoveryAction(_Base):
    action: str
    params: dict[str, Any] = Field(default_factory=dict)
    rationale: str


class RecoveryPlan(_Base):
    plan_id: str
    hypothesis_id: Optional[str] = None
    actions: list[RecoveryAction] = Field(default_factory=list)
    risk_level: RiskLevel
    blast_radius: str
    rollback_plan: str
    status: str = "PROPOSED"
    dropped_invalid_actions: int = 0
    created_at: str


def validated(model: type[BaseModel], data: dict) -> dict:
    """Validate `data` against `model` and return it as a plain dict (extras kept).
    Raises pydantic.ValidationError when the contract is broken."""
    return model.model_validate(data).model_dump()


# --------------------------------------------------------------------- report


class EvidenceRef(_Base):
    evidence_id: str
    tool: str
    agent: str


class IncidentReport(_Base):
    """Final structured output of an investigation (course requirement 3)."""

    incident_id: str
    description: str
    outcome: str  # DIAGNOSED | ABSTAINED | RESOLVED | ...
    reason: str = ""
    root_cause: Optional[str] = None
    root_cause_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    supporting_evidence: list[EvidenceRef] = Field(default_factory=list)
    critic_verdict: Optional[Verdict] = None
    critic_rationale: Optional[str] = None
    rejected_hypotheses: list[str] = Field(default_factory=list)
    recovery_actions: list[str] = Field(default_factory=list)
    approval: Optional[str] = None
    loops_used: int = 0
    total_tokens: Optional[int] = None
    llm_calls: Optional[int] = None

    def to_markdown(self) -> str:
        lines = [
            f"# Incident report {self.incident_id}",
            "",
            f"**Outcome:** {self.outcome}  ",
            f"**Reason:** {self.reason or 'n/a'}  ",
            f"**Re-evaluation loops used:** {self.loops_used}",
            "",
            "## Root cause",
            "",
        ]
        if self.root_cause:
            conf = f" (confidence {self.root_cause_confidence:.0%})" if self.root_cause_confidence is not None else ""
            lines.append(f"{self.root_cause}{conf}")
        else:
            lines.append("No root cause was supported; the system abstained.")
        lines += ["", "## Critic", ""]
        if self.critic_verdict:
            lines.append(f"Verdict: **{self.critic_verdict}**. {self.critic_rationale or ''}".rstrip())
        else:
            lines.append("No critic review was recorded.")
        if self.rejected_hypotheses:
            lines += ["", "Rejected hypotheses:"] + [f"- {h}" for h in self.rejected_hypotheses]
        lines += ["", "## Supporting evidence", ""]
        if self.supporting_evidence:
            lines += ["| Evidence | Tool | Agent |", "|---|---|---|"]
            lines += [f"| {e.evidence_id} | {e.tool} | {e.agent} |" for e in self.supporting_evidence]
        else:
            lines.append("None cited.")
        lines += ["", "## Recovery", ""]
        if self.recovery_actions:
            lines += [f"- {a}" for a in self.recovery_actions]
            lines.append(f"\nApproval: {self.approval or 'n/a'}")
        else:
            lines.append("No recovery plan was proposed.")
        lines += ["", "## Cost", ""]
        if self.total_tokens is None:
            lines.append("Token usage not recorded.")
        else:
            lines.append(f"{self.llm_calls} model calls, {self.total_tokens} tokens.")
        return "\n".join(lines) + "\n"


def build_incident_report(incident: dict) -> IncidentReport:
    """Build the final report from a stored incident dict (pure, no I/O)."""
    decision = incident.get("decision") or {}
    hypotheses = incident.get("hypotheses") or []
    critiques = incident.get("critic_results") or []
    plan = incident.get("recovery_plan") or {}
    usage = (incident.get("token_usage") or {}).get("total") or {}

    winner = next((h for h in hypotheses if h.get("status") == "SUPPORTED"), None)
    pool: dict[str, tuple[str, str]] = {}
    for agent, finding in (incident.get("agent_findings") or {}).items():
        for ev in (finding or {}).get("evidence", []) or []:
            pool[ev.get("evidence_id")] = (ev.get("tool", "?"), agent)
    refs = []
    if winner:
        for eid in winner.get("supporting_evidence_ids", []):
            tool, agent = pool.get(eid, ("unknown", "unknown"))
            refs.append(EvidenceRef(evidence_id=eid, tool=tool, agent=agent))
    last = critiques[-1] if critiques else {}
    return IncidentReport(
        incident_id=incident.get("incident_id", "unknown"),
        description=incident.get("description", ""),
        outcome=incident.get("status") or decision.get("outcome", "UNKNOWN"),
        reason=decision.get("reason", ""),
        root_cause=winner.get("statement") if winner else None,
        root_cause_confidence=winner.get("confidence") if winner else None,
        supporting_evidence=refs,
        critic_verdict=last.get("verdict"),
        critic_rationale=last.get("rationale"),
        rejected_hypotheses=[h.get("statement", "") for h in hypotheses if h.get("status") == "REJECTED"],
        recovery_actions=[a.get("action", "") for a in plan.get("actions", [])],
        approval=(incident.get("approval_state") or {}).get("decision"),
        loops_used=decision.get("loops_used", 0),
        total_tokens=usage.get("total_tokens"),
        llm_calls=usage.get("llm_calls"),
    )
