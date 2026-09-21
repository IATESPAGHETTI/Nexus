import { useQuery } from "@tanstack/react-query";
import { getIncident, getIncidentEvents } from "./client";
import type {
  AgentRuntimeStatus,
  DiagnosticAgentName,
  IncidentState,
  NexusEvent,
} from "./types";
import { DIAGNOSTIC_AGENTS } from "./types";

const POLL_INTERVAL_MS = 1500;

// Keep polling through DIAGNOSED too, not just INVESTIGATING — the real
// recovery flow (propose -> validate -> approve -> execute -> verify) runs
// entirely while status stays "DIAGNOSED" (root CLAUDE.md section 20;
// orchestrator/recovery.py only ever moves it to RESOLVED on verified
// success). Only ABSTAINED/RESOLVED are genuinely terminal.
const LIVE_STATUSES = new Set(["INVESTIGATING", "DIAGNOSED"]);

export function useIncidentQuery(incidentId: string | undefined) {
  return useQuery({
    queryKey: ["incident", incidentId],
    queryFn: () => getIncident(incidentId as string),
    enabled: Boolean(incidentId),
    refetchInterval: (query) =>
      query.state.data && LIVE_STATUSES.has(query.state.data.status) ? POLL_INTERVAL_MS : false,
    refetchIntervalInBackground: true,
  });
}

export function useIncidentEventsQuery(incidentId: string | undefined) {
  return useQuery({
    queryKey: ["incident-events", incidentId],
    queryFn: () => getIncidentEvents(incidentId as string),
    enabled: Boolean(incidentId),
    refetchInterval: POLL_INTERVAL_MS,
    refetchIntervalInBackground: true,
  });
}

export interface AgentRuntimeState {
  status: AgentRuntimeStatus;
  currentAction: string | null;
  findingsCount: number;
}

/**
 * Derives each diagnostic agent's operational status purely from the real
 * event log + incident state — never a separate/invented state machine.
 * Events are processed in emission order so a re-investigation round
 * (EVIDENCE_REQUESTED -> AGENT_STARTED again) is reflected correctly.
 */
export function deriveAgentStates(
  incident: IncidentState | undefined,
  events: NexusEvent[] | undefined,
): Record<DiagnosticAgentName, AgentRuntimeState> {
  const result = Object.fromEntries(
    DIAGNOSTIC_AGENTS.map((name) => [
      name,
      { status: "IDLE", currentAction: null, findingsCount: 0 } as AgentRuntimeState,
    ]),
  ) as Record<DiagnosticAgentName, AgentRuntimeState>;

  if (!events) return result;

  // numeric: event ids are "evt-<n>"; a plain string compare puts evt-10 before evt-2.
  const ordered = [...events].sort((a, b) =>
    a.event_id.localeCompare(b.event_id, undefined, { numeric: true }),
  );

  for (const evt of ordered) {
    // orchestrator/investigation.py emits AGENT_STARTED as source=incident_manager,
    // target=<agent> (the agent it dispatched); every other event names the agent
    // as its source. Reading source for AGENT_STARTED meant agents never showed
    // as RUNNING.
    const agent = (evt.event_type === "AGENT_STARTED" && evt.target ? evt.target : evt.source) as DiagnosticAgentName;
    if (!DIAGNOSTIC_AGENTS.includes(agent)) {
      // EVIDENCE_REQUESTED is emitted with the *target* agent, not source.
      if (
        evt.event_type === "EVIDENCE_REQUESTED" &&
        evt.target &&
        DIAGNOSTIC_AGENTS.includes(evt.target as DiagnosticAgentName)
      ) {
        result[evt.target as DiagnosticAgentName].status = "WAITING";
      }
      continue;
    }

    switch (evt.event_type) {
      case "AGENT_STARTED":
        result[agent].status = "RUNNING";
        break;
      case "MCP_TOOL_CALL": {
        const tool = evt.payload?.tool;
        if (typeof tool === "string") {
          result[agent].currentAction = tool;
        }
        break;
      }
      case "AGENT_COMPLETED":
        result[agent].status = evt.status === "failed" ? "FAILED" : "COMPLETED";
        result[agent].currentAction = null;
        break;
      default:
        break;
    }
  }

  if (incident) {
    for (const agent of DIAGNOSTIC_AGENTS) {
      const finding = incident.agent_findings[agent];
      result[agent].findingsCount = finding ? finding.evidence.length : 0;
    }
  }

  return result;
}
