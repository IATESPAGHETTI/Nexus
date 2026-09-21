import { motion } from "motion/react";
import type { SemanticTone } from "./semantics";
import styles from "./ConfidenceBar.module.css";

interface ConfidenceBarProps {
  value: number; // 0..1
  tone?: SemanticTone;
  compact?: boolean;
  showValue?: boolean;
}

function toneClass(tone: SemanticTone | undefined) {
  if (!tone || tone === "neutral") return "";
  return styles[tone];
}

export function ConfidenceBar({
  value,
  tone,
  compact = false,
  showValue = true,
}: ConfidenceBarProps) {
  const pct = Math.round(Math.max(0, Math.min(1, value)) * 100);
  return (
    <div className={`${styles.wrap} ${compact ? styles.compact : ""}`}>
      <div className={styles.track}>
        <motion.div
          className={`${styles.fill} ${toneClass(tone)}`}
          initial={false}
          animate={{ width: `${pct}%` }}
          transition={{ type: "spring", stiffness: 260, damping: 32 }}
        />
      </div>
      {showValue && <span className={`${styles.value} nx-tabular`}>{pct}%</span>}
    </div>
  );
}
