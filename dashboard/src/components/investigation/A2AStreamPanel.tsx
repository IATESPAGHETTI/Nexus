import { motion, AnimatePresence } from "motion/react";
import { CollapsibleSection } from "../primitives/CollapsibleSection";
import { Timestamp } from "../primitives/Timestamp";
import { MonoLabel } from "../primitives/MonoLabel";
import { Badge } from "../primitives/Badge";
import type { A2ARow } from "../../lib/derive";
import styles from "./EventTable.module.css";

export function A2AStreamPanel({ rows }: { rows: A2ARow[] }) {
  return (
    <CollapsibleSection
      title="A2A communication"
      meta={`${rows.length} messages`}
      hint="Network communication between independently running agents."
      defaultOpen
    >
      <div className={styles.table}>
        {rows.length === 0 && <div className={styles.empty}>No A2A activity yet.</div>}
        <AnimatePresence initial={false}>
          {rows
            .slice()
            .reverse()
            .map((row) => (
              <motion.div
                key={row.key}
                className={styles.row}
                initial={{ opacity: 0, y: -4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
              >
                <div className={styles.rowHead}>
                  <span className={styles.flow}>
                    <MonoLabel>{row.sender}</MonoLabel>
                    <span className={styles.arrow}>&rarr;</span>
                    <MonoLabel>{row.recipient}</MonoLabel>
                  </span>
                  <Badge tone={row.status === "completed" ? "green" : "neutral"}>{row.status}</Badge>
                </div>
                <div className={styles.rowHead}>
                  <span className={styles.flow}>
                    {row.task_id ? <MonoLabel>{row.task_id}</MonoLabel> : "task dispatch"}
                  </span>
                  <Timestamp iso={row.timestamp} />
                </div>
              </motion.div>
            ))}
        </AnimatePresence>
      </div>
    </CollapsibleSection>
  );
}
