import { motion } from "motion/react";
import { useAgentControl } from "../../context/AgentControlContext";
import { useActiveIncident } from "../../api/useActiveIncident";
import {
  EVENT_LABELS,
  VERDICT_LABELS,
  countEvents,
  recentActivity,
  type AgentKey,
  type NodeStatus,
} from "../../lib/presentation";
import styles from "./LivePipelineSection.module.css";

// Plain-English key shown under the diagram (brief section 8): a fixed
// translation table, not data.
const TRANSLATION_KEY: [string, string][] = [
  ["MCP_TOOL_CALL", EVENT_LABELS.MCP_TOOL_CALL],
  ["EVIDENCE_FOUND", EVENT_LABELS.EVIDENCE_FOUND],
  ["HYPOTHESIS_CREATED", EVENT_LABELS.HYPOTHESIS_CREATED],
  ["CRITIC_CHALLENGE", EVENT_LABELS.CRITIC_CHALLENGE],
  ["INSUFFICIENT_EVIDENCE", VERDICT_LABELS.INSUFFICIENT_EVIDENCE],
  ["ABSTENTION", EVENT_LABELS.ABSTENTION],
  ["RECOVERY_PROPOSED", EVENT_LABELS.RECOVERY_PROPOSED],
  ["HUMAN_APPROVAL_GRANTED", EVENT_LABELS.HUMAN_APPROVAL_GRANTED],
];

const STATE_CLASS: Record<NodeStatus, string> = {
  idle: "",
  working: "nodeWorking",
  reported: "nodeReported",
  failed: "nodeFailed",
};

const STATE_WORD: Record<NodeStatus, string> = {
  idle: "not involved yet",
  working: "working now",
  reported: "reported",
  failed: "no response",
};

interface NodeLive {
  status: NodeStatus;
  note: string | null;
}

interface AgentNodeProps {
  name: string;
  shortName: string;
  /** real reachability probe (agents ON + backend up), else undefined */
  isOnline?: boolean;
  /** real per-incident state derived from events, else undefined */
  live?: NodeLive;
  delay: number;
}

function AgentNode({ name, shortName, isOnline, live, delay }: AgentNodeProps) {
  const dot =
    live && live.status !== "idle"
      ? live.status === "working"
        ? styles.dotWorking
        : live.status === "failed"
        ? styles.dotOffline
        : styles.dotOnline
      : isOnline === true
      ? styles.dotOnline
      : isOnline === false
      ? styles.dotOffline
      : styles.dotNeutral;
  return (
    <motion.div
      className={`${styles.agentNode} ${live ? styles[STATE_CLASS[live.status]] ?? "" : ""}`}
      initial={{ opacity: 0, x: -16 }}
      whileInView={{ opacity: 1, x: 0 }}
      viewport={{ once: true, margin: "-30px" }}
      transition={{ duration: 0.4, delay }}
    >
      <span className={`${styles.agentDot} ${dot}`} />
      <div className={styles.agentNodeLabel}>
        <div className={styles.agentNodeName}>{name}</div>
        <div className={styles.agentNodeShort}>
          {live && live.status !== "idle" ? `${STATE_WORD[live.status]}${live.note ? ` — ${live.note}` : ""}` : shortName}
        </div>
      </div>
    </motion.div>
  );
}

interface SynthesisNodeProps {
  name: string;
  color: string;
  delay: number;
  live?: NodeLive;
}

function SynthesisNode({ name, color, delay, live }: SynthesisNodeProps) {
  return (
    <motion.div
      className={`${styles.synthesisNode} ${live ? styles[STATE_CLASS[live.status]] ?? "" : ""}`}
      style={{ borderColor: `${color}50`, background: `${color}0d` }}
      initial={{ opacity: 0, scale: 0.9 }}
      whileInView={{ opacity: 1, scale: 1 }}
      viewport={{ once: true, margin: "-30px" }}
      transition={{ duration: 0.4, delay }}
    >
      <span className={styles.synthesisNodeLabel} style={{ color }}>
        {name}
      </span>
      {live && live.status !== "idle" && (
        <span className={styles.nodeNote}>
          {STATE_WORD[live.status]}
          {live.note ? ` — ${live.note}` : ""}
        </span>
      )}
    </motion.div>
  );
}

export function LivePipelineSection() {
  const { agentsEnabled, backendReachable, demoStatus, isLoading: probing } = useAgentControl();
  const { model, events } = useActiveIncident();
  const feed = recentActivity(events, 8);
  const counts = countEvents(events);
  const nodeLive = (key: AgentKey): NodeLive | undefined => (model ? model.pipeline[key] : undefined);

  const agentOnlineMap = demoStatus?.agents ?? {};

  // Determine whether to show real status indicators
  const showLiveStatus = agentsEnabled && backendReachable;
  const showUnreachable = agentsEnabled && !probing && !backendReachable;

  const getAgentOnline = (agentKey: string): boolean | undefined => {
    if (!showLiveStatus) return undefined;
    return agentOnlineMap[agentKey] ?? false;
  };

  return (
    <section id="pres-pipeline" className={styles.section}>
      <div className={styles.container}>
        {/* Section Header */}
        <motion.div
          className={styles.header}
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <div className={styles.eyebrow}>LIVE AGENT PIPELINE</div>
          <h2 className={styles.title}>
            How the Agents{" "}
            <span className={styles.titleAccent}>Work Together</span>
          </h2>
          <p className={styles.subtitle}>
            Four diagnostic agents investigate in parallel, then hand their findings to the Evidence
            Agent, which forms a hypothesis. The Root-Cause Critic challenges it. If proven, the
            Recovery Agent proposes a fix — and waits for human approval.
          </p>
        </motion.div>

        {/* Status banner */}
        {showUnreachable ? (
          <div className={styles.unreachableBanner}>
            
            <div>
              <div className={styles.bannerTitle}>BACKEND UNREACHABLE</div>
              <div className={styles.bannerBody}>
                Agents toggled ON but FastAPI backend could not be reached on port 8000. The
                diagram below is structural only — no live status is shown.
              </div>
            </div>
          </div>
        ) : !agentsEnabled ? (
          <div className={styles.offlineBanner}>
            
            <div>
              <div className={styles.bannerTitle}>ILLUSTRATIVE DIAGRAM</div>
              <div className={styles.bannerBody}>
                Agents are currently OFF. This diagram shows the fixed architecture of the NEXUS
                pipeline — not live activity. Toggle{" "}
                <strong>NEXUS AGENTS: ON</strong> to see real agent status.
              </div>
            </div>
          </div>
        ) : !showLiveStatus ? (
          <div className={styles.offlineBanner}>
            <div>
              <div className={styles.bannerTitle}>CONNECTING…</div>
              <div className={styles.bannerBody}>Probing the backend. No status is shown until it answers.</div>
            </div>
          </div>
        ) : (
          <div className={styles.liveBanner}>
            
            <div>
              <div className={styles.bannerTitle}>LIVE STATUS</div>
              <div className={styles.bannerBody}>
                Connected to the backend ({demoStatus?.agents_reachable_count ?? 0}/{demoStatus?.agents_total ?? 7} agent
                services reachable).{" "}
                {model
                  ? "Node states below are derived from this incident's real events; amber means working right now."
                  : "No incident yet — dots show reachability only."}
              </div>
            </div>
          </div>
        )}

        {/* Pipeline Diagram */}
        <motion.div
          className={styles.pipelineWrapper}
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-40px" }}
          transition={{ duration: 0.6, delay: 0.1 }}
        >
          <div className={styles.pipeline}>
            {/* Left column: 4 Diagnostic Agents */}
            <div className={styles.diagnosticCol}>
              <div className={styles.colLabel}>DIAGNOSTIC AGENTS</div>
              <div className={styles.diagnosticAgents}>
                <AgentNode
                  name="Metrics Agent"
                  shortName="checks system vitals"
                  isOnline={getAgentOnline("metrics_agent")}
                  live={nodeLive("metrics_agent")}
                  delay={0.2}
                />
                <AgentNode
                  name="Logs & Traces Agent"
                  shortName="checks symptoms"
                  isOnline={getAgentOnline("logs_traces_agent")}
                  live={nodeLive("logs_traces_agent")}
                  delay={0.28}
                />
                <AgentNode
                  name="Change Analysis Agent"
                  shortName="checks what changed"
                  isOnline={getAgentOnline("change_analysis_agent")}
                  live={nodeLive("change_analysis_agent")}
                  delay={0.36}
                />
                <AgentNode
                  name="Database Agent"
                  shortName="checks DB health"
                  isOnline={getAgentOnline("database_agent")}
                  live={nodeLive("database_agent")}
                  delay={0.44}
                />
              </div>
            </div>

            {/* Arrow from diagnostics → Evidence */}
            <div className={styles.arrowCol}>
              <div className={styles.arrowLines}>
                {[0, 1, 2, 3].map((i) => (
                  <div key={i} className={styles.arrowLine} />
                ))}
                <div className={styles.arrowMerge} />
              </div>
              <div className={styles.arrowHead}>→</div>
            </div>

            {/* Center: Evidence Agent */}
            <div className={styles.centerCol}>
              <div className={styles.colLabel}>SYNTHESIS</div>
              <SynthesisNode
                name="Evidence Agent"
                color="#8a9aff"
                delay={0.5}
                live={nodeLive("evidence_agent")}
              />

              {/* Re-evaluation loop indicator */}
              <div className={styles.reEvalLoop}>
                <div className={styles.reEvalLine} />
                <span className={styles.reEvalLabel}>Re-evaluation loop</span>
                <div className={styles.reEvalLine} />
              </div>
            </div>

            {/* Arrow Evidence → Critic */}
            <div className={styles.simpleArrow}>→</div>

            {/* Critic */}
            <div className={styles.centerCol}>
              <div className={styles.colLabel}>CHALLENGE</div>
              <SynthesisNode
                name="Root-Cause Critic"
                color="#f0656a"
                delay={0.58}
                live={nodeLive("root_cause_critic")}
              />
            </div>

            {/* Arrow Critic → Recovery */}
            <div className={styles.simpleArrow}>→</div>

            {/* Recovery */}
            <div className={styles.centerCol}>
              <div className={styles.colLabel}>RECOVERY</div>
              <SynthesisNode
                name="Recovery Agent"
                color="#6fcf97"
                delay={0.66}
                live={nodeLive("recovery_agent")}
              />
              <div className={styles.humanApproval}>
                
                <span className={styles.humanApprovalLabel}>Human Approval Required</span>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Real activity feed: only when a real incident is being followed */}
        {showLiveStatus && (
          <div className={styles.feedBox}>
            <div className={styles.translationTitle}>
              Live activity
              {model && (
                <span className={styles.feedCounts}>
                  {counts.mcp} system check{counts.mcp === 1 ? "" : "s"} · {counts.a2a} agent message
                  {counts.a2a === 1 ? "" : "s"} · {counts.evidence} evidence report{counts.evidence === 1 ? "" : "s"}
                </span>
              )}
            </div>
            {feed.length ? (
              <ul className={styles.feedList}>
                {feed.map((f) => (
                  <li key={f.id} className={styles.feedRow}>
                    <span className={styles.feedTime}>{new Date(f.time).toLocaleTimeString()}</span>
                    <span className={styles.feedLabel}>{f.label}</span>
                    <span className={styles.feedActor}>
                      {f.actor}
                      {f.detail ? ` · ${f.detail}` : ""}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className={styles.feedEmpty}>No events yet. Nothing is shown until the backend records something real.</p>
            )}
          </div>
        )}

        {/* Event Translation Key */}
        <motion.div
          className={styles.translationKey}
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5, delay: 0.3 }}
        >
          <div className={styles.translationTitle}>Plain-English Event Labels</div>
          <div className={styles.translationGrid}>
            {TRANSLATION_KEY.map(([technical, human]) => (
              <div key={technical} className={styles.translationRow}>
                <code className={styles.technicalLabel}>{technical}</code>
                <span className={styles.translationArrow}>→</span>
                <span className={styles.humanLabel}>{human}</span>
              </div>
            ))}
          </div>
        </motion.div>
      </div>
    </section>
  );
}
