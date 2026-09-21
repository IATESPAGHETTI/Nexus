import { useEffect, useMemo } from "react";
import { useAgentControl } from "../context/AgentControlContext";
import { loadRecentIncidents, rememberIncident } from "../lib/recentIncidents";
import { buildCommandCenterModel } from "../lib/presentation";
import { useIncidentEventsQuery, useIncidentQuery } from "./useIncident";

/**
 * The single real incident the Presentation page follows. Only queries the
 * backend when agents are ON and the backend is reachable; otherwise returns
 * nothing (never a substitute incident).
 */
export function useActiveIncident() {
  const { agentsEnabled, backendReachable, activeIncidentId } = useAgentControl();
  const live = agentsEnabled && backendReachable;
  const candidate = activeIncidentId ?? loadRecentIncidents()[0]?.incident_id;

  const incidentQuery = useIncidentQuery(live ? candidate : undefined);
  const eventsQuery = useIncidentEventsQuery(live ? candidate : undefined);
  const incident = live ? incidentQuery.data : undefined;
  const events = live ? eventsQuery.data : undefined;

  useEffect(() => {
    if (incident) rememberIncident(incident);
  }, [incident]);

  const model = useMemo(
    () => (incident ? buildCommandCenterModel(incident, events) : null),
    [incident, events],
  );

  return {
    live,
    incidentId: candidate,
    incident,
    events,
    model,
    // e.g. backend restarted and no longer knows the remembered incident
    incidentMissing: live && Boolean(candidate) && incidentQuery.isError,
    isLoading: live && Boolean(candidate) && incidentQuery.isLoading,
  };
}
