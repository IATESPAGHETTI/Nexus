import type { TokenUsage } from "../../api/types";
import { GlassSurface } from "../primitives/GlassSurface";
import { MonoLabel } from "../primitives/MonoLabel";
import { StatusDot } from "../primitives/StatusDot";
import styles from "./UsagePanel.module.css";

const fmt = (n: number) => n.toLocaleString("en-US");

/**
 * Root CLAUDE.md section 8: never invent quota/usage numbers. Everything shown
 * here is what the agents themselves reported for this incident
 * (`orchestrator/budget.py` -> `incident.token_usage`) against NEXUS's own
 * configured limits. The provider's remaining quota is NOT captured anywhere,
 * so it is always labelled unavailable rather than guessed.
 */
export function UsagePanel({ usage }: { usage?: TokenUsage | null }) {
  const total = usage?.total;
  const limits = usage?.limits;
  const agents = Object.entries(usage?.by_agent ?? {});

  return (
    <GlassSurface className={styles.wrap} light>
      <div className={styles.title}>LLM usage</div>

      {total ? (
        <>
          <div className={styles.row}>
            <span className={styles.label}>Model calls</span>
            <span className={styles.value}>
              {fmt(total.llm_calls)}
              {limits ? ` / ${fmt(limits.max_llm_calls)}` : ""}
            </span>
          </div>
          <div className={styles.row}>
            <span className={styles.label}>Tokens</span>
            <span className={styles.value}>
              {fmt(total.total_tokens)}
              {limits ? ` / ${fmt(limits.max_total_tokens)}` : ""}
            </span>
          </div>

          {usage?.budget_exceeded && (
            <div className={styles.body}>
              <StatusDot tone="amber" />
              <span className={styles.warn}>
                Spending limit reached: {usage.budget_exceeded}. NEXUS stopped instead of spending more.
              </span>
            </div>
          )}

          {agents.length > 0 && (
            <div className={styles.agents}>
              {agents.map(([name, counts]) => (
                <div className={styles.row} key={name}>
                  <MonoLabel>{name}</MonoLabel>
                  <span className={styles.value}>
                    {fmt(counts.llm_calls)} calls · {fmt(counts.total_tokens)} tokens
                  </span>
                </div>
              ))}
            </div>
          )}

          {!!usage?.unmeasured_tasks && (
            <div className={styles.note}>
              {usage.unmeasured_tasks} agent task(s) reported no token counts and are counted as 1 call each.
            </div>
          )}
        </>
      ) : (
        <div className={styles.body}>
          <StatusDot tone="neutral" />
          <span className={styles.text}>No model usage recorded for this incident yet</span>
        </div>
      )}

      <div className={styles.note}>Provider quota: unavailable from provider</div>
    </GlassSurface>
  );
}
