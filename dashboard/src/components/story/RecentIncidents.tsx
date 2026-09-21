import { useMemo } from "react";
import { Link } from "react-router-dom";
import { useQueries } from "@tanstack/react-query";
import { motion } from "motion/react";
import { getIncident } from "../../api/client";
import { loadRecentIncidents } from "../../lib/recentIncidents";
import { SectionMarker } from "./StorySections";
import styles from "./RecentIncidents.module.css";

const STATUS_LABEL: Record<string, string> = {
  INVESTIGATING: "Investigating",
  DIAGNOSED: "Root cause supported",
  ABSTAINED: "Abstained",
  RESOLVED: "Recovered",
};

/** Per-browser list of incidents this browser has opened; each is re-fetched live. */
export function RecentIncidents() {
  const cached = useMemo(() => loadRecentIncidents(), []);
  const results = useQueries({
    queries: cached.map((entry) => ({
      queryKey: ["incident", entry.incident_id],
      queryFn: () => getIncident(entry.incident_id),
      retry: 0,
      staleTime: 5_000,
    })),
  });
  const rows = cached.map((entry, i) => results[i]?.data ?? entry);

  return (
    <section id="recent-incidents" className={styles.section}>
      <div className={styles.container}>
        <SectionMarker label="Recent incidents" />
        <h2 className={styles.title}>
          Every investigation leaves an audit trail.
          <span> Open one to see every event, message and piece of evidence.</span>
        </h2>

        {rows.length === 0 ? (
          <div className={styles.empty}>
            <div className={styles.emptyTitle}>No incidents recorded in this browser yet</div>
            <p>Run the demo from the live system above. Its incident will appear here.</p>
          </div>
        ) : (
          <ul className={styles.list}>
            {rows.map((inc, i) => (
              <motion.li
                key={inc.incident_id}
                initial={{ opacity: 0, y: 18 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-30px" }}
                transition={{ duration: 0.45, delay: Math.min(i, 6) * 0.05 }}
              >
                <Link to={`/incidents/${encodeURIComponent(inc.incident_id)}`} className={styles.row}>
                  <span className={styles.id}>{inc.incident_id}</span>
                  <span className={styles.desc}>{inc.description}</span>
                  <span className={styles.status}>{STATUS_LABEL[inc.status] ?? inc.status}</span>
                  <span className={styles.go}>→</span>
                </Link>
              </motion.li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
