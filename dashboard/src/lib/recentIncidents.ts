// Phase 7 deliberately does NOT add a GET /incidents list endpoint to
// backend/ (see docs/PROJECT_STATE.md "Next" / dashboard/CLAUDE.md) — that is
// scoped as a small follow-up backend enhancement once the UI itself is
// proven. Until then, the home page's incident list is a per-viewer
// convenience: it remembers which real incident_ids this browser has opened,
// purely so returning here doesn't require re-typing an ID. It is never the
// source of truth for an incident's data — InvestigationPage always re-fetches
// live state from backend/ for the id, and the cached summary shown here is
// refreshed opportunistically. Read/write are wrapped defensively; if storage
// is unavailable the home page just shows the manual-lookup box.
import type { IncidentState } from "../api/types";

const KEY = "nexus.recentIncidents.v1";

export interface RecentIncidentEntry {
  incident_id: string;
  description: string;
  status: IncidentState["status"];
  created_at: string;
  updated_at: string;
}

export function loadRecentIncidents(): RecentIncidentEntry[] {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed;
  } catch {
    return [];
  }
}

export function rememberIncident(incident: IncidentState): void {
  try {
    const existing = loadRecentIncidents().filter(
      (e) => e.incident_id !== incident.incident_id,
    );
    const entry: RecentIncidentEntry = {
      incident_id: incident.incident_id,
      description: incident.description,
      status: incident.status,
      created_at: incident.created_at,
      updated_at: incident.updated_at,
    };
    const next = [entry, ...existing].slice(0, 20);
    localStorage.setItem(KEY, JSON.stringify(next));
  } catch {
    // Best-effort only — never block rendering on storage availability.
  }
}
