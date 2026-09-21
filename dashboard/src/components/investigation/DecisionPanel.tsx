import { motion } from "motion/react";
import { GlassSurface } from "../primitives/GlassSurface";
import type { Decision, Hypothesis } from "../../api/types";
import styles from "./DecisionPanel.module.css";

interface DecisionPanelProps {
  decision: Decision;
  hypotheses: Hypothesis[];
}

export function DecisionPanel({ decision, hypotheses }: DecisionPanelProps) {
  const isDiagnosed = decision.outcome === "DIAGNOSED";
  const supported = hypotheses.find((h) => h.status === "SUPPORTED");

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 240, damping: 30 }}
    >
      <GlassSurface elevation="raised" className={styles.wrap}>
        <span className={styles.eyebrow}>{isDiagnosed ? "Diagnosis reached" : "Investigation abstained"}</span>
        <span className={`${styles.headline} ${isDiagnosed ? styles.green : styles.amber}`}>
          {isDiagnosed ? supported?.statement ?? decision.reason : "NO SUFFICIENTLY SUPPORTED ROOT CAUSE"}
        </span>
        <span className={styles.detail}>
          {isDiagnosed
            ? decision.reason
            : `Investigation terminated after ${decision.loops_used} evaluation cycle${
                decision.loops_used === 1 ? "" : "s"
              }.`}
        </span>
        <span className={styles.meta}>
          {decision.loops_used} of {decision.max_loops} re-evaluation cycles used
        </span>
      </GlassSurface>
    </motion.div>
  );
}
