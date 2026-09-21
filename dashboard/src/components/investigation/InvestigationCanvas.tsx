import { GlassSurface } from "../primitives/GlassSurface";
import { ConfidenceBar } from "../primitives/ConfidenceBar";
import { Badge } from "../primitives/Badge";
import { AgentCard } from "./AgentCard";
import { agentStatusTone, hypothesisStatusTone, type SemanticTone } from "../primitives/semantics";
import type { AgentRuntimeState } from "../../api/useIncident";
import type { Hypothesis } from "../../api/types";
import styles from "./InvestigationCanvas.module.css";

function toneVar(tone: SemanticTone): string {
  switch (tone) {
    case "green":
      return "var(--nx-green)";
    case "amber":
      return "var(--nx-amber)";
    case "red":
      return "var(--nx-red)";
    default:
      return "var(--nx-border-hairline-strong)";
  }
}

interface InvestigationCanvasProps {
  agentStates: Record<string, AgentRuntimeState>;
  leadingHypothesis: Hypothesis | null;
}

/**
 * The spatial "what is NEXUS doing right now?" centerpiece — the 4
 * diagnostic agents above/below and beside the current leading hypothesis
 * (if one exists yet). A simple flow-based 3-row layout (not absolute
 * positioning — an earlier version used absolute-positioned "compass
 * point" placement and broke under real viewport widths, confirmed live
 * before this fix). The connector bars are a real-state indicator, not
 * decoration: each one's color is the real agentStatusTone() of the agent
 * it touches (idle=hairline gray, running=amber, completed=green,
 * failed=red) — derived the same way AgentCard's own status dot is, from
 * the real event log only.
 */
export function InvestigationCanvas({ agentStates, leadingHypothesis }: InvestigationCanvasProps) {
  const metricsTone = agentStatusTone(agentStates.metrics_agent?.status ?? "IDLE");
  const databaseTone = agentStatusTone(agentStates.database_agent?.status ?? "IDLE");
  const logsTone = agentStatusTone(agentStates.logs_traces_agent?.status ?? "IDLE");
  const changeTone = agentStatusTone(agentStates.change_analysis_agent?.status ?? "IDLE");
  const centerTone = leadingHypothesis ? hypothesisStatusTone(leadingHypothesis.status) : "neutral";

  return (
    <GlassSurface elevation="raised" className={styles.canvas}>
      <div className={styles.rowSide}>
        <div className={styles.agentSlot}>
          <AgentCard agentName="metrics_agent" state={agentStates.metrics_agent} />
        </div>
      </div>
      <div className={styles.connectorV} style={{ background: toneVar(metricsTone) }} />

      <div className={styles.rowMiddle}>
        <div
          className={styles.agentSlot}
          style={{ borderRight: `2px solid ${toneVar(logsTone)}`, paddingRight: "var(--nx-space-3)" }}
        >
          <AgentCard agentName="logs_traces_agent" state={agentStates.logs_traces_agent} />
        </div>

        <GlassSurface strong className={styles.center}>
          {leadingHypothesis ? (
            <>
              <span className={styles.centerEyebrow}>{leadingHypothesis.hypothesis_id} — current hypothesis</span>
              <span className={styles.centerStatement}>{leadingHypothesis.statement}</span>
              <ConfidenceBar value={leadingHypothesis.confidence} tone={centerTone} />
              <Badge tone={centerTone}>{leadingHypothesis.status}</Badge>
            </>
          ) : (
            <>
              <span className={styles.centerEyebrow}>Investigation</span>
              <span className={styles.centerEmpty}>No hypothesis formed yet — waiting on agent evidence.</span>
            </>
          )}
        </GlassSurface>

        <div
          className={styles.agentSlot}
          style={{ borderLeft: `2px solid ${toneVar(changeTone)}`, paddingLeft: "var(--nx-space-3)" }}
        >
          <AgentCard agentName="change_analysis_agent" state={agentStates.change_analysis_agent} />
        </div>
      </div>

      <div className={styles.connectorV} style={{ background: toneVar(databaseTone) }} />
      <div className={styles.rowSide}>
        <div className={styles.agentSlot}>
          <AgentCard agentName="database_agent" state={agentStates.database_agent} />
        </div>
      </div>
    </GlassSurface>
  );
}
