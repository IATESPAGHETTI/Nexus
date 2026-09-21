// Presentation-layer derivations: turn REAL backend state (IncidentState +
// event log) into plain-English structures for the Presentation page.
//
// Hard rule (dashboard/CLAUDE.md, brief section 5): nothing here invents
// data. Every string shown to a viewer is either (a) a fixed label that
// translates a real event/verdict/action name, or (b) text the real agents
// produced (finding interpretation, hypothesis statement, critic rationale).
// When real data is absent the model says so ("not yet", "none") instead of
// substituting a plausible-sounding sentence.

import { deriveAgentStates } from "../api/useIncident";
import type {
  ActionHistoryEntry,
  ApprovalState,
  Critique,
  CritiqueVerdict,
  Finding,
  Hypothesis,
  IncidentState,
  IncidentStatus,
  NexusEvent,
  RecoveryPlan,
} from "../api/types";

// ---------------------------------------------------------------- labels --

export const EVENT_LABELS: Record<string, string> = {
  INCIDENT_CREATED: "Incident opened",
  INCIDENT_STATUS_CHANGED: "Incident status updated",
  AGENT_STARTED: "Agent began investigating",
  AGENT_COMPLETED: "Agent finished investigating",
  A2A_MESSAGE_SENT: "Agents exchanged a message",
  MCP_TOOL_CALL: "Agent ran a system check",
  MCP_TOOL_RESULT: "System check returned results",
  EVIDENCE_FOUND: "Agent reported evidence",
  EVIDENCE_REQUESTED: "More evidence requested",
  HYPOTHESIS_CREATED: "Possible cause proposed",
  HYPOTHESIS_UPDATED: "Possible cause updated",
  CRITIC_CHALLENGE: "Diagnosis challenged",
  RE_EVALUATION_STARTED: "Re-evaluating the diagnosis",
  DIAGNOSIS_REACHED: "Root cause supported",
  ABSTENTION: "NEXUS declined to guess",
  RECOVERY_PROPOSED: "Recovery plan proposed",
  SAFETY_VALIDATION: "Recovery plan safety-checked",
  HUMAN_APPROVAL_REQUESTED: "Waiting for human approval",
  HUMAN_APPROVAL_GRANTED: "Human approved the recovery",
  HUMAN_APPROVAL_REJECTED: "Human declined the recovery",
  RECOVERY_EXECUTED: "Recovery action executed",
  RECOVERY_VERIFIED: "Recovery check completed",
  INCIDENT_RESOLVED: "Incident resolved",
};

export function humanEventLabel(type: string): string {
  return EVENT_LABELS[type] ?? type.toLowerCase().replace(/_/g, " ");
}

export const VERDICT_LABELS: Record<CritiqueVerdict, string> = {
  SUPPORTED: "Supported",
  CONTRADICTED: "Contradicted by the evidence",
  INSUFFICIENT_EVIDENCE: "Not proven yet",
  REQUEST_MORE_EVIDENCE: "More evidence needed",
  ABSTAIN: "Declined to conclude",
};

export const HYPOTHESIS_STATUS_LABELS: Record<string, string> = {
  PROPOSED: "Proposed",
  UNDER_REVIEW: "Under review",
  CHALLENGED: "Challenged",
  NEEDS_EVIDENCE: "Needs more evidence",
  SUPPORTED: "Supported",
  REJECTED: "Rejected",
  ABSTAINED: "Not proven",
};

export const ACTION_LABELS: Record<string, string> = {
  restart_service: "Restart the service",
  rollback_deployment: "Roll back to the previous deployment",
  reset_config: "Reset configuration to its known-good values",
  scale_resources: "Restore service resources",
};

const TOOL_LABELS: Record<string, string> = {
  get_metrics: "service metrics",
  query_logs: "logs",
  get_trace: "request traces",
  get_recent_deployments: "recent deployments",
  get_git_diff: "recent code changes",
  get_database_stats: "database health",
  run_diagnostic: "a diagnostic",
};

export type AgentKey =
  | "metrics_agent"
  | "logs_traces_agent"
  | "change_analysis_agent"
  | "database_agent"
  | "evidence_agent"
  | "root_cause_critic"
  | "recovery_agent";

export interface AgentInfo {
  key: AgentKey;
  name: string;
  role: string;
}

export const PIPELINE_AGENTS: AgentInfo[] = [
  { key: "metrics_agent", name: "Metrics Agent", role: "checks system vitals" },
  { key: "logs_traces_agent", name: "Logs & Traces Agent", role: "checks symptoms and request behavior" },
  { key: "change_analysis_agent", name: "Change Analysis Agent", role: "checks what recently changed" },
  { key: "database_agent", name: "Database Agent", role: "checks database health" },
  { key: "evidence_agent", name: "Evidence Agent", role: "combines observations into possible causes" },
  { key: "root_cause_critic", name: "Root-Cause Critic", role: "gives a second opinion" },
  { key: "recovery_agent", name: "Recovery Agent", role: "proposes a bounded fix" },
];

const ACTOR_NAMES: Record<string, string> = {
  ...Object.fromEntries(PIPELINE_AGENTS.map((a) => [a.key, a.name])),
  incident_manager: "Incident Manager",
  guardrails: "Safety guardrails",
  human: "Human operator",
};

export function actorName(source: string | undefined): string {
  if (!source) return "NEXUS";
  return ACTOR_NAMES[source] ?? source;
}

// ------------------------------------------------------------- pipeline ---

export type NodeStatus = "idle" | "working" | "reported" | "failed";

export interface PipelineNode {
  status: NodeStatus;
  note: string | null;
}

function eventSeq(e: NexusEvent): number {
  const n = Number(e.event_id.replace(/^\D+/, ""));
  return Number.isFinite(n) ? n : 0;
}

export function orderEvents(events: NexusEvent[] | undefined): NexusEvent[] {
  return [...(events ?? [])].sort((a, b) => eventSeq(a) - eventSeq(b));
}

/**
 * Per-agent operational state, derived only from real events/state.
 *
 * Diagnostic agents: exactly the existing deriveAgentStates() (AGENT_STARTED /
 * AGENT_COMPLETED). The three reasoning agents emit no "started" event of
 * their own, so "working" is derived from real, ordered event counts:
 *   Evidence Agent  working = a dispatch round has fully completed (every
 *                     AGENT_STARTED matched by an AGENT_COMPLETED) but the
 *                     matching A2A reply from the Evidence Agent has not been
 *                     recorded yet.
 *   Critic          working = RE_EVALUATION_STARTED count > CRITIC_CHALLENGE
 *                     count (emitted immediately before / after the real call).
 *   Recovery Agent  working = DIAGNOSIS_REACHED recorded, RECOVERY_PROPOSED not.
 */
export function derivePipeline(
  incident: IncidentState | undefined,
  events: NexusEvent[] | undefined,
): Record<AgentKey, PipelineNode> {
  const ordered = orderEvents(events);
  const diag = deriveAgentStates(incident, ordered);
  const terminal = incident?.status === "ABSTAINED" || incident?.status === "RESOLVED";

  const out = {} as Record<AgentKey, PipelineNode>;
  for (const name of Object.keys(diag) as (keyof typeof diag)[]) {
    const s = diag[name];
    const status: NodeStatus =
      s.status === "RUNNING" || s.status === "WAITING"
        ? "working"
        : s.status === "COMPLETED"
        ? "reported"
        : s.status === "FAILED"
        ? "failed"
        : "idle";
    let note: string | null = null;
    if (status === "working") note = s.currentAction ? `running a check: ${toolLabel(s.currentAction)}` : "investigating";
    else if (status === "reported") note = s.findingsCount ? `${s.findingsCount} system check${s.findingsCount === 1 ? "" : "s"} reported` : "reported";
    else if (status === "failed") note = "did not report back";
    out[name] = { status, note };
  }

  let outstanding = 0;
  let roundsDone = 0;
  let evidenceReplies = 0;
  let reEvalStarted = 0;
  let criticChallenges = 0;
  let diagnosed = false;
  let recoveryProposed = false;
  for (const e of ordered) {
    if (e.event_type === "AGENT_STARTED") outstanding += 1;
    else if (e.event_type === "AGENT_COMPLETED") {
      outstanding = Math.max(0, outstanding - 1);
      if (outstanding === 0) roundsDone += 1;
    } else if (e.event_type === "A2A_MESSAGE_SENT" && e.target === "evidence_agent") evidenceReplies += 1;
    else if (e.event_type === "RE_EVALUATION_STARTED") reEvalStarted += 1;
    else if (e.event_type === "CRITIC_CHALLENGE") criticChallenges += 1;
    else if (e.event_type === "DIAGNOSIS_REACHED") diagnosed = true;
    else if (e.event_type === "RECOVERY_PROPOSED") recoveryProposed = true;
  }

  const hypothesisCount = incident?.hypotheses.length ?? 0;
  const evidenceWorking = roundsDone > evidenceReplies && !terminal;
  out.evidence_agent = evidenceWorking
    ? { status: "working", note: "combining findings into possible causes" }
    : evidenceReplies > 0
    ? {
        status: "reported",
        note: hypothesisCount ? `${hypothesisCount} possible cause${hypothesisCount === 1 ? "" : "s"}` : "no possible cause proposed",
      }
    : { status: "idle", note: null };

  const reviews = incident?.critic_results.length ?? 0;
  out.root_cause_critic =
    reEvalStarted > criticChallenges && !terminal
      ? { status: "working", note: "challenging the leading explanation" }
      : criticChallenges > 0
      ? { status: "reported", note: `${reviews || criticChallenges} review${(reviews || criticChallenges) === 1 ? "" : "s"} completed` }
      : { status: "idle", note: null };

  out.recovery_agent = recoveryProposed
    ? { status: "reported", note: "recovery plan proposed" }
    : diagnosed && incident?.status === "DIAGNOSED"
    ? { status: "working", note: "drafting a bounded recovery plan" }
    : { status: "idle", note: null };

  return out;
}

export function toolLabel(tool: string): string {
  return TOOL_LABELS[tool] ?? tool;
}

// ----------------------------------------------------------- event feed ---

export interface FeedItem {
  id: string;
  time: string;
  label: string;
  actor: string;
  detail: string | null;
}

export function recentActivity(events: NexusEvent[] | undefined, limit = 10): FeedItem[] {
  return orderEvents(events)
    .filter((e) => e.event_type !== "MCP_TOOL_RESULT")
    .slice(-limit)
    .reverse()
    .map((e) => {
      let detail: string | null = null;
      if (e.event_type === "MCP_TOOL_CALL" && typeof e.payload?.tool === "string") {
        detail = `checked ${toolLabel(e.payload.tool)}`;
      } else if (e.event_type === "A2A_MESSAGE_SENT" && e.target) {
        detail = `to ${actorName(e.target)}`;
      } else if (e.event_type === "AGENT_COMPLETED" && e.status === "failed") {
        detail = "no response received";
      }
      return { id: e.event_id, time: e.timestamp, label: humanEventLabel(e.event_type), actor: actorName(e.source), detail };
    });
}

export function countEvents(events: NexusEvent[] | undefined) {
  const list = events ?? [];
  return {
    total: list.length,
    a2a: list.filter((e) => e.event_type === "A2A_MESSAGE_SENT").length,
    mcp: list.filter((e) => e.event_type === "MCP_TOOL_CALL").length,
    evidence: list.filter((e) => e.event_type === "EVIDENCE_FOUND").length,
  };
}

// ------------------------------------------------------- command center ---

export interface EvidenceLine {
  agent: string;
  text: string;
  checks: number;
}

export interface Reason {
  label: string;
  items: string[];
}

export type RecoveryStage =
  | "AWAITING_APPROVAL"
  | "REJECTED_BY_SAFETY"
  | "DECLINED"
  | "EXPIRED"
  | "EXECUTING"
  | "EXECUTION_FAILED"
  | "VERIFYING"
  | "VERIFICATION_FAILED"
  | "RECOVERED";

export interface VerificationCheck {
  path: string;
  medianMs: number;
  failures: number;
  requests: number;
}

export interface RecoveryView {
  stage: RecoveryStage;
  /** the real post-recovery live probe (orchestrator/recovery.py), if it has run */
  verification: { limitMs: number; checks: VerificationCheck[] } | null;
  actions: { label: string; rationale?: string }[];
  risk: string;
  blastRadius?: string;
  rollbackPlan?: string;
  approval: ApprovalState | null;
  history: ActionHistoryEntry[];
}

export interface CommandCenterModel {
  incidentId: string;
  description: string;
  status: IncidentStatus;
  createdAt: string;
  updatedAt: string;
  latest: FeedItem | null;
  pipeline: Record<AgentKey, PipelineNode>;
  findings: EvidenceLine[];
  silentAgents: string[];
  belief: {
    statement: string;
    confidencePct: number;
    statusLabel: string;
    supporting: EvidenceLine[];
    contradicting: EvidenceLine[];
    missing: string[];
  } | null;
  challenge: {
    verdict: CritiqueVerdict;
    verdictLabel: string;
    rationale: string;
    contradictions: string[];
    assumptions: string[];
    alternatives: string[];
    requested: string[];
    reviews: number;
  } | null;
  decision: {
    kind: "INVESTIGATING" | "DIAGNOSED" | "ABSTAINED" | "RESOLVED";
    reason: string | null;
    loopsUsed: number | null;
    maxLoops: number | null;
    reasons: Reason[];
  };
  recovery: RecoveryView | null;
}

function pickLeadingHypothesis(incident: IncidentState): Hypothesis | undefined {
  const supported = incident.hypotheses.filter((h) => h.status === "SUPPORTED");
  const pool = supported.length ? supported : incident.hypotheses;
  return pool.reduce<Hypothesis | undefined>(
    (best, h) => (!best || h.confidence > best.confidence ? h : best),
    undefined,
  );
}

function evidenceToAgent(incident: IncidentState): Map<string, string> {
  const map = new Map<string, string>();
  for (const [agent, finding] of Object.entries(incident.agent_findings ?? {})) {
    for (const ev of finding?.evidence ?? []) map.set(ev.evidence_id, agent);
  }
  return map;
}

function findingText(f: Finding): string {
  return (f.interpretation || "").trim() || (f.observation || "").trim();
}

function linesFor(ids: string[], incident: IncidentState, owner: Map<string, string>): EvidenceLine[] {
  const counts = new Map<string, number>();
  for (const id of ids) {
    const agent = owner.get(id);
    if (agent) counts.set(agent, (counts.get(agent) ?? 0) + 1);
  }
  return [...counts.entries()].map(([agent, checks]) => ({
    agent: actorName(agent),
    text: findingText(incident.agent_findings[agent]) || "(the agent reported no written interpretation)",
    checks,
  }));
}

function recoveryView(
  incident: IncidentState,
  ordered: NexusEvent[],
): RecoveryView | null {
  const plan: RecoveryPlan | null = incident.recovery_plan;
  if (!plan) return null;
  const approval = incident.approval_state;
  const executed = [...ordered].reverse().find((e) => e.event_type === "RECOVERY_EXECUTED");
  const verified = [...ordered].reverse().find((e) => e.event_type === "RECOVERY_VERIFIED");

  let stage: RecoveryStage;
  if (incident.status === "RESOLVED") stage = "RECOVERED";
  else if (!approval || approval.decision === "PENDING") stage = "AWAITING_APPROVAL";
  else if (approval.decision === "NOT_REQUESTED") stage = "REJECTED_BY_SAFETY";
  else if (approval.decision === "REJECTED") stage = "DECLINED";
  else if (approval.decision === "EXPIRED") stage = "EXPIRED";
  else if (!executed) stage = "EXECUTING";
  else if (executed.payload && executed.payload.all_succeeded === false) stage = "EXECUTION_FAILED";
  else if (!verified) stage = "VERIFYING";
  else stage = "VERIFICATION_FAILED";

  let verification: RecoveryView["verification"] = null;
  const probe = verified?.payload?.probe as
    | { latency_limit_ms?: number; per_path?: Record<string, { median_ms: number; failures: number; requests: number }> }
    | undefined;
  if (probe?.per_path) {
    verification = {
      limitMs: probe.latency_limit_ms ?? 0,
      checks: Object.entries(probe.per_path).map(([path, v]) => ({
        path,
        medianMs: v.median_ms,
        failures: v.failures,
        requests: v.requests,
      })),
    };
  }

  return {
    stage,
    verification,
    actions: (plan.actions ?? []).map((a) => ({
      label: ACTION_LABELS[a.action] ?? a.action.replace(/_/g, " "),
      rationale: a.rationale,
    })),
    risk: plan.risk_level,
    blastRadius: plan.blast_radius,
    rollbackPlan: plan.rollback_plan,
    approval,
    history: incident.action_history ?? [],
  };
}

export function buildCommandCenterModel(
  incident: IncidentState,
  events: NexusEvent[] | undefined,
): CommandCenterModel {
  const ordered = orderEvents(events);
  const owner = evidenceToAgent(incident);
  const pipeline = derivePipeline(incident, ordered);

  const findings: EvidenceLine[] = [];
  const silentAgents: string[] = [];
  for (const [agent, status] of Object.entries(pipeline)) {
    if (agent === "evidence_agent" || agent === "root_cause_critic" || agent === "recovery_agent") continue;
    const finding = incident.agent_findings?.[agent];
    if (finding) {
      findings.push({ agent: actorName(agent), text: findingText(finding) || "(no written interpretation)", checks: finding.evidence.length });
    } else if (status.status === "failed") {
      silentAgents.push(actorName(agent));
    }
  }

  const leading = pickLeadingHypothesis(incident);
  const critique: Critique | undefined =
    (leading && [...incident.critic_results].reverse().find((c) => c.hypothesis_id === leading.hypothesis_id)) ||
    incident.critic_results[incident.critic_results.length - 1];

  const belief = leading
    ? {
        statement: leading.statement,
        confidencePct: Math.round(leading.confidence * 100),
        statusLabel: HYPOTHESIS_STATUS_LABELS[leading.status] ?? leading.status,
        supporting: linesFor(leading.supporting_evidence_ids ?? [], incident, owner),
        contradicting: linesFor(leading.contradicting_evidence_ids ?? [], incident, owner),
        missing: leading.missing_evidence ?? [],
      }
    : null;

  const challenge = critique
    ? {
        verdict: critique.verdict,
        verdictLabel: VERDICT_LABELS[critique.verdict] ?? critique.verdict,
        rationale: critique.rationale,
        contradictions: critique.contradictions ?? [],
        assumptions: critique.unsupported_assumptions ?? [],
        alternatives: critique.alternative_explanations ?? [],
        requested: critique.requested_evidence ?? [],
        reviews: incident.critic_results.length,
      }
    : null;

  // Abstention reasons: ONLY those actually present in the real critique /
  // hypothesis / agent data — never a canned list.
  const reasons: Reason[] = [];
  if (incident.status === "ABSTAINED") {
    if (!leading) {
      reasons.push({
        label: "No possible cause could be formed",
        items: silentAgents.length
          ? [`These agents did not report back: ${silentAgents.join(", ")}.`]
          : ["The evidence gathered did not support proposing a cause."],
      });
    }
    if (challenge && (challenge.verdict === "INSUFFICIENT_EVIDENCE" || challenge.verdict === "REQUEST_MORE_EVIDENCE")) {
      reasons.push({ label: "Insufficient evidence", items: challenge.rationale ? [challenge.rationale] : [] });
    }
    const conflicts = [...(challenge?.contradictions ?? [])];
    if (belief?.contradicting.length) conflicts.push(...belief.contradicting.map((c) => `${c.agent}: ${c.text}`));
    if (conflicts.length) reasons.push({ label: "Conflicting telemetry", items: conflicts });
    if (belief?.missing.length) reasons.push({ label: "Missing direct observation", items: belief.missing });
    if (challenge?.assumptions.length) reasons.push({ label: "Unsupported causal link", items: challenge.assumptions });
  }

  return {
    incidentId: incident.incident_id,
    description: incident.description,
    status: incident.status,
    createdAt: incident.created_at,
    updatedAt: incident.updated_at,
    latest: recentActivity(events, 1)[0] ?? null,
    pipeline,
    findings,
    silentAgents,
    belief,
    challenge,
    decision: {
      kind: incident.status,
      reason: incident.decision?.reason ?? null,
      loopsUsed: incident.decision?.loops_used ?? null,
      maxLoops: incident.decision?.max_loops ?? null,
      reasons,
    },
    recovery: recoveryView(incident, ordered),
  };
}
