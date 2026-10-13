import { motion } from "motion/react";
import { StageTracker } from "./StageTracker";
import { useAgentControl } from "../../context/AgentControlContext";
import { useActiveIncident } from "../../api/useActiveIncident";
import {
  EVENT_LABELS,
  VERDICT_LABELS,
  countEvents,
  recentActivity,
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

export function LivePipelineSection() {
  const { agentsEnabled, backendReachable, demoStatus, isLoading: probing } = useAgentControl();
  const { model, events } = useActiveIncident();
  const feed = recentActivity(events, 8);
  const counts = countEvents(events);

  // Determine whether to show real status indicators
  const showLiveStatus = agentsEnabled && backendReachable;
  const showUnreachable = agentsEnabled && !probing && !backendReachable;

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

        {/* Fixed stage tracker: states/results are real incident data (or hidden) */}
        <StageTracker live={showLiveStatus} model={model} />

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
