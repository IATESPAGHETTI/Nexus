import { GlassSurface } from "../primitives/GlassSurface";
import { StatusDot } from "../primitives/StatusDot";
import type { IncidentState } from "../../api/types";
import styles from "./UsagePanel.module.css";

type AgentTotals = { llm_calls?: number; total_tokens?: number };

/**
 * Root CLAUDE.md section 8: never invent quota/usage numbers. Shows only what the
 * provider reported through LiteLLM and the orchestrator summed into
 * `incident.token_usage`; when nothing was reported it says so.
 */
export function UsagePanel({ incident }: { incident?: IncidentState }) {
  const usage = (incident?.token_usage ?? {}) as Record<string, unknown>;
  const total = typeof usage.total_tokens === "number" ? usage.total_tokens : 0;
  if (!total) {
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
  const byAgent = Object.entries((usage.by_agent ?? {}) as Record<string, AgentTotals>);
  return (
    <GlassSurface className={styles.wrap} light>
      <div className={styles.title}>LLM usage</div>
      <div className={styles.figure}>{total.toLocaleString()} tokens</div>
      <div className={styles.text}>
        {String(usage.llm_calls ?? 0)} model calls · {Number(usage.prompt_tokens ?? 0).toLocaleString()} prompt ·{" "}
        {Number(usage.completion_tokens ?? 0).toLocaleString()} completion
      </div>
      <ul className={styles.list}>
        {byAgent.map(([name, a]) => (
          <li key={name}>
            <span>{name}</span>
            <span>{(a.total_tokens ?? 0).toLocaleString()}</span>
          </li>
        ))}
      </ul>
      <div className={styles.text}>Provider-reported, this incident. Quota and dollar cost are not available.</div>
    </GlassSurface>
  );
}
