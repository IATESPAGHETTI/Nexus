import { motion } from "motion/react";
import { PHASES } from "../../lib/derive";
import styles from "./PhaseTimeline.module.css";

export function PhaseTimeline({ currentIndex }: { currentIndex: number }) {
  return (
    <div className={styles.row}>
      {PHASES.map((phase, i) => (
        <div key={phase} className={styles.node} style={{ display: "flex", alignItems: "center" }}>
          <div className={styles.node}>
            <span
              className={`${styles.dot} ${i <= currentIndex ? styles.reached : ""} ${
                i === currentIndex ? styles.current : ""
              }`}
            />
            <span
              className={`${styles.label} ${i <= currentIndex ? styles.reached : ""} ${
                i === currentIndex ? styles.current : ""
              }`}
            >
              {phase}
            </span>
          </div>
          {i < PHASES.length - 1 && (
            <div className={styles.connector}>
              <motion.div
                className={styles.connectorFill}
                initial={false}
                animate={{ x: i < currentIndex ? "0%" : "-100%" }}
                transition={{ type: "spring", stiffness: 220, damping: 30 }}
              />
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
