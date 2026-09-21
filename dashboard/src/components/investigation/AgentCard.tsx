import { motion, AnimatePresence } from "motion/react";
import { GlassSurface } from "../primitives/GlassSurface";
import { StatusDot } from "../primitives/StatusDot";
import { MonoLabel } from "../primitives/MonoLabel";
import { agentStatusTone } from "../primitives/semantics";
import type { AgentRuntimeState } from "../../api/useIncident";
import styles from "./AgentCard.module.css";

const DISPLAY_NAME: Record<string, string> = {
  metrics_agent: "Metrics",
  logs_traces_agent: "Logs & Traces",
  change_analysis_agent: "Change Analysis",
  database_agent: "Database",
};

// "Professor mode" (root CLAUDE.md-adjacent UX principle, per the Phase 10
// live-command-center brief): each agent understandable in one sentence, as
// a native tooltip — never a tutorial overlay.
const DESCRIPTION: Record<string, string> = {
  metrics_agent: "Investigates service-level performance and error-rate signals.",
  logs_traces_agent: "Investigates structured logs and request traces for the incident window.",
  change_analysis_agent: "Investigates recent deployments and configuration changes.",
  database_agent: "Investigates database query performance and diagnostics.",
};

export function AgentCard({ agentName, state }: { agentName: string; state: AgentRuntimeState }) {
  return (
    <GlassSurface className={styles.card}>
      <div className={styles.head} title={DESCRIPTION[agentName]}>
        <StatusDot tone={agentStatusTone(state.status)} />
        <span className={styles.name}>{DISPLAY_NAME[agentName] ?? agentName}</span>
        <span className={styles.statusLabel}>{state.status}</span>
      </div>
      <div className={styles.action}>
        <AnimatePresence mode="wait">
          {state.currentAction && (
            <motion.span
              key={state.currentAction}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.15 }}
            >
              <MonoLabel>{state.currentAction}</MonoLabel>
            </motion.span>
          )}
        </AnimatePresence>
      </div>
      <div className={styles.footer}>
        <span>{state.findingsCount} evidence item{state.findingsCount === 1 ? "" : "s"}</span>
      </div>
    </GlassSurface>
  );
}
