import type { SemanticTone } from "./semantics";
import styles from "./StatusDot.module.css";

export function StatusDot({ tone }: { tone: SemanticTone }) {
  return <span className={`${styles.dot} ${styles[tone]}`} aria-hidden />;
}
