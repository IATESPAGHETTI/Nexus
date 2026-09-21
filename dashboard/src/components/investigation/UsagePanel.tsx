import { GlassSurface } from "../primitives/GlassSurface";
import { StatusDot } from "../primitives/StatusDot";
import styles from "./UsagePanel.module.css";

/**
 * Root CLAUDE.md section 8: never invent quota/usage numbers. No token/usage
 * metadata is captured anywhere in the Phase 6 pipeline yet (see
 * docs/PROJECT_STATE.md "Next") — this is a real, designed empty state, not a
 * placeholder chart with fabricated numbers.
 */
export function UsagePanel() {
  return (
    <GlassSurface className={styles.wrap} light>
      <div className={styles.title}>LLM usage</div>
      <div className={styles.body}>
        <StatusDot tone="neutral" />
        <span className={styles.text}>Unavailable from provider</span>
      </div>
    </GlassSurface>
  );
}
