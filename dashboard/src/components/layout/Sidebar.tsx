import { useMemo } from "react";
import { Link, useLocation, useParams } from "react-router-dom";
import { useQueries } from "@tanstack/react-query";
import { getIncident } from "../../api/client";
import { useDemoStatus } from "../../api/useDemoStatus";
import { StatusDot } from "../primitives/StatusDot";
import { MonoLabel } from "../primitives/MonoLabel";
import { incidentStatusTone } from "../primitives/semantics";
import { loadRecentIncidents } from "../../lib/recentIncidents";
import styles from "./Sidebar.module.css";

const LIVE_STATUSES = new Set(["INVESTIGATING", "DIAGNOSED"]);

/**
 * Persistent left navigation — real data only. "Active Incidents"/"Recent
 * Incidents" are this browser's real, previously-opened incident_ids
 * (src/lib/recentIncidents.ts), each re-fetched live so their status dot
 * reflects the actual current backend state, not a stale cached snapshot —
 * never a fabricated incident list (no `GET /incidents` list endpoint
 * exists yet; see dashboard/CLAUDE.md).
 */
export function Sidebar() {
  const location = useLocation();
  const { incidentId: activeIncidentId } = useParams<{ incidentId: string }>();
  const cached = useMemo(() => loadRecentIncidents(), [location.pathname]);
  const demoStatus = useDemoStatus();

  const results = useQueries({
    queries: cached.map((entry) => ({
      queryKey: ["incident", entry.incident_id],
      queryFn: () => getIncident(entry.incident_id),
      retry: 0,
      staleTime: 5_000,
    })),
  });
  const incidents = cached.map((entry, i) => results[i]?.data ?? entry);
  const active = incidents.filter((i) => LIVE_STATUSES.has(i.status));
  const recent = incidents.filter((i) => !LIVE_STATUSES.has(i.status));

  return (
    <nav className={styles.sidebar}>
      <Link to="/" className={styles.wordmark}>
        NEXUS
      </Link>

      <div className={styles.section}>
        <Link to="/" className={`${styles.navLink} ${location.pathname === "/" ? styles.active : ""}`}>
          Mission Control
        </Link>
      </div>

      <div className={styles.section}>
        <div className={styles.sectionTitle}>Active Incidents</div>
        {active.length === 0 ? (
          <div className={styles.empty}>None right now</div>
        ) : (
          active.map((incident) => (
            <Link
              key={incident.incident_id}
              to={`/incidents/${encodeURIComponent(incident.incident_id)}`}
              className={`${styles.incidentLink} ${activeIncidentId === incident.incident_id ? styles.active : ""}`}
            >
              <StatusDot tone={incidentStatusTone(incident.status)} />
              <div className={styles.incidentText}>
                <div className={styles.incidentId}>
                  <MonoLabel>{incident.incident_id}</MonoLabel>
                </div>
                <div className={styles.incidentDesc}>{incident.description}</div>
              </div>
            </Link>
          ))
        )}
      </div>

      <div className={styles.section}>
        <div className={styles.sectionTitle}>Recent Incidents</div>
        {recent.length === 0 ? (
          <div className={styles.empty}>None yet</div>
        ) : (
          recent.slice(0, 8).map((incident) => (
            <Link
              key={incident.incident_id}
              to={`/incidents/${encodeURIComponent(incident.incident_id)}`}
              className={`${styles.incidentLink} ${activeIncidentId === incident.incident_id ? styles.active : ""}`}
            >
              <StatusDot tone={incidentStatusTone(incident.status)} />
              <div className={styles.incidentText}>
                <div className={styles.incidentId}>
                  <MonoLabel>{incident.incident_id}</MonoLabel>
                </div>
                <div className={styles.incidentDesc}>{incident.description}</div>
              </div>
            </Link>
          ))
        )}
      </div>

      <div className={styles.spacer} />

      <div className={styles.section}>
        <div className={styles.sectionTitle}>System Status</div>
        <div className={styles.statusBlock}>
          <div className={styles.statusRow}>
            <StatusDot tone={demoStatus.data?.production_reachable ? "green" : "red"} />
            Production {demoStatus.data ? (demoStatus.data.production_reachable ? "healthy" : "unreachable") : "checking…"}
          </div>
          <div className={styles.statusRow}>
            <StatusDot
              tone={
                demoStatus.data
                  ? demoStatus.data.agents_reachable_count === demoStatus.data.agents_total
                    ? "green"
                    : demoStatus.data.agents_reachable_count > 0
                      ? "amber"
                      : "neutral"
                  : "neutral"
              }
            />
            Agents {demoStatus.data ? `${demoStatus.data.agents_reachable_count}/${demoStatus.data.agents_total} online` : "checking…"}
          </div>
        </div>
      </div>
    </nav>
  );
}
