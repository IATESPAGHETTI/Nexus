import { motion, AnimatePresence } from "motion/react";
import { CollapsibleSection } from "../primitives/CollapsibleSection";
import { Timestamp } from "../primitives/Timestamp";
import { MonoLabel } from "../primitives/MonoLabel";
import { Badge } from "../primitives/Badge";
import type { McpRow } from "../../lib/derive";
import styles from "./EventTable.module.css";

export function MCPActivityPanel({ rows }: { rows: McpRow[] }) {
  return (
    <CollapsibleSection
      title="MCP diagnostic activity"
      meta={`${rows.length} tool calls`}
      hint="Standardized interface used by agents to retrieve production evidence."
      defaultOpen
    >
      <div className={styles.table}>
        {rows.length === 0 && <div className={styles.empty}>No MCP tool activity yet.</div>}
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
                    <MonoLabel>{row.agent}</MonoLabel>
                    <span className={styles.arrow}>&middot;</span>
                    <MonoLabel>{row.tool}</MonoLabel>
                  </span>
                  <Badge tone={row.status === "ok" ? "green" : "neutral"}>{row.status}</Badge>
                </div>
                <div className={styles.rowHead}>
                  <span className={styles.flow} title={row.resultSummary}>
                    {row.resultSummary}
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
