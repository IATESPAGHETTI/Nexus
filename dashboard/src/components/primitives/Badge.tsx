import type { PropsWithChildren } from "react";
import type { SemanticTone } from "./semantics";
import styles from "./Badge.module.css";

export function Badge({ tone, children }: PropsWithChildren<{ tone: SemanticTone }>) {
  return <span className={`${styles.badge} ${styles[tone]}`}>{children}</span>;
}
