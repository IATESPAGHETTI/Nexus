import type { EvidenceItem, Hypothesis, IncidentState, NexusEvent } from "../api/types";

export type Phase = "DETECTED" | "INVESTIGATING" | "EVIDENCE" | "CRITIC" | "DIAGNOSIS";
export const PHASES: Phase[] = ["DETECTED", "INVESTIGATING", "EVIDENCE", "CRITIC", "DIAGNOSIS"];

/** Current phase derived purely from which real event types have actually
 * been emitted for this incident — never a guessed/timed progression. */
export function derivePhaseIndex(events: NexusEvent[] | undefined): number {
  if (!events || events.length === 0) return 0;
  const types = new Set(events.map((e) => e.event_type));
  let idx = 0;
  if (types.has("INCIDENT_CREATED")) idx = Math.max(idx, 0);
  if (types.has("AGENT_STARTED")) idx = Math.max(idx, 1);
  if (types.has("EVIDENCE_FOUND") || types.has("HYPOTHESIS_CREATED")) idx = Math.max(idx, 2);
  if (types.has("CRITIC_CHALLENGE") || types.has("RE_EVALUATION_STARTED")) idx = Math.max(idx, 3);
  if (types.has("DIAGNOSIS_REACHED") || types.has("ABSTENTION")) idx = Math.max(idx, 4);
  return idx;
}

export interface EvidenceLookupEntry extends EvidenceItem {
  agent: string;
}

/** Maps every real evidence_id (across all agent findings) to its full item
 * + originating agent, so hypothesis evidence_ids can be resolved to real
 * observation/tool/result data for display. */
export function buildEvidenceLookup(
  incident: IncidentState | undefined,
): Record<string, EvidenceLookupEntry> {
  const map: Record<string, EvidenceLookupEntry> = {};
  if (!incident) return map;
  for (const [agent, finding] of Object.entries(incident.agent_findings)) {
    for (const item of finding.evidence) {
      map[item.evidence_id] = { ...item, agent };
    }
  }
  return map;
}

export function openHypotheses(hypotheses: Hypothesis[] | undefined): Hypothesis[] {
  if (!hypotheses) return [];
  const OPEN = new Set(["PROPOSED", "UNDER_REVIEW", "NEEDS_EVIDENCE", "CHALLENGED", "SUPPORTED"]);
  return hypotheses.filter((h) => OPEN.has(h.status) || h.status === "REJECTED" || h.status === "ABSTAINED");
}

export interface A2ARow {
  key: string;
  timestamp: string;
  sender: string;
  recipient: string;
  status: string;
  task_id?: string;
}

export function a2aRows(events: NexusEvent[] | undefined): A2ARow[] {
  if (!events) return [];
  return events
    .filter((e) => e.event_type === "A2A_MESSAGE_SENT")
    .map((e) => ({
      key: e.event_id,
      timestamp: e.timestamp,
      sender: e.source,
      recipient: e.target ?? "?",
      status: e.status ?? "unknown",
      task_id: typeof e.payload?.task_id === "string" ? e.payload.task_id : undefined,
    }));
}

export interface McpRow {
  key: string;
  timestamp: string;
  agent: string;
  tool: string;
  argsSummary: string;
  status: string;
  resultSummary: string;
}

function summarize(value: unknown, max = 60): string {
  try {
    const s = typeof value === "string" ? value : JSON.stringify(value);
    return s.length > max ? `${s.slice(0, max)}…` : s;
  } catch {
    return String(value);
  }
}

/** Pairs MCP_TOOL_CALL/MCP_TOOL_RESULT events (matched by evidence_id) with
 * the real result payload already present in the Finding's evidence list —
 * MCP_TOOL_RESULT events themselves carry no result data (see
 * orchestrator/investigation.py), only the evidence_id/tool that identifies
 * which real evidence item to resolve. */
export function mcpRows(
  events: NexusEvent[] | undefined,
  evidenceLookup: Record<string, EvidenceLookupEntry>,
): McpRow[] {
  if (!events) return [];
  return events
    .filter((e) => e.event_type === "MCP_TOOL_CALL")
    .map((e) => {
      const evidenceId = typeof e.payload?.evidence_id === "string" ? e.payload.evidence_id : undefined;
      const resolved = evidenceId ? evidenceLookup[evidenceId] : undefined;
      return {
        key: e.event_id,
        timestamp: e.timestamp,
        agent: e.source,
        tool: typeof e.payload?.tool === "string" ? e.payload.tool : "?",
        argsSummary: summarize(e.payload?.arguments ?? resolved?.arguments ?? {}),
        status: e.status ?? "unknown",
        resultSummary: resolved ? summarize(resolved.result) : "(pending)",
      };
    });
}
