import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { MonoLabel } from "../primitives/MonoLabel";
import type { EvidenceLookupEntry } from "../../lib/derive";
import styles from "./EvidenceNode.module.css";

interface EvidenceNodeProps {
  evidenceId: string;
  entry: EvidenceLookupEntry | undefined;
  side: "left" | "right";
  index: number;
}

function summarizeResult(result: unknown): string {
  try {
    return JSON.stringify(result, null, 2);
  } catch {
    return String(result);
  }
}

export function EvidenceNode({ evidenceId, entry, side, index }: EvidenceNodeProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      layout
      layoutId={`evidence-${evidenceId}`}
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0 }}
      transition={{ type: "spring", stiffness: 260, damping: 28, delay: index * 0.04 }}
    >
      <div
        className={`${styles.node} ${side === "left" ? styles.left : styles.right}`}
        onClick={() => setExpanded((v) => !v)}
      >
        <div className={styles.connector} />
        <div className={styles.body}>
          <div className={styles.id}>
            <MonoLabel>{evidenceId}</MonoLabel>
          </div>
          <div className={styles.tool}>
            {entry ? <MonoLabel>{entry.tool}</MonoLabel> : "evidence"}
            {entry && <span style={{ color: "var(--nx-ink-4)" }}> · {entry.agent.replace("_agent", "")}</span>}
          </div>
          <AnimatePresence>
            {expanded && entry && (
              <motion.div
                className={styles.expanded}
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 32 }}
              >
                {summarizeResult(entry.result).slice(0, 400)}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </motion.div>
  );
}
