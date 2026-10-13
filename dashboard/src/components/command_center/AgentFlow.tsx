import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { skippedAgents } from "../../lib/conversation";
import type { NexusEvent } from "../../api/types";
import { PIPELINE_AGENTS, type AgentKey, type CommandCenterModel, type NodeStatus } from "../../lib/presentation";
import styles from "./AgentFlow.module.css";

interface Props {
  model: CommandCenterModel;
  events: NexusEvent[] | undefined;
  /** false = nothing is investigating; the map stays still */
  animated: boolean;
}

const INVESTIGATORS: AgentKey[] = ["metrics_agent", "logs_traces_agent", "change_analysis_agent", "database_agent"];
const REASONERS: AgentKey[] = ["evidence_agent", "root_cause_critic", "recovery_agent"];

const STATE_WORD: Record<NodeStatus, string> = {
  idle: "waiting",
  working: "working",
  reported: "replied",
  failed: "no reply",
};

/**
 * Live map of the real message flow. The Incident Manager is the A2A client;
 * every agent is its own service. A dot travels DOWN a wire while the agent is
 * working on a request and UP once (the “callback”) when its reply is recorded.
 * Every state comes from derivePipeline(), i.e. from real events.
 */
export function AgentFlow({ model, events, animated }: Props) {
  const skipped = skippedAgents(events);
  const prev = useRef<Partial<Record<AgentKey, NodeStatus>>>({});
  const [callbacks, setCallbacks] = useState<Record<string, number>>({});

  // working -> reported/failed = a callback just arrived; flash it once.
  useEffect(() => {
    const fresh: AgentKey[] = [];
    for (const a of PIPELINE_AGENTS) {
      const was = prev.current[a.key];
      const now = model.pipeline[a.key].status;
      if (was === "working" && (now === "reported" || now === "failed")) fresh.push(a.key);
      prev.current[a.key] = now;
    }
    if (!fresh.length) return;
    const stamp = Date.now();
    setCallbacks((c) => ({ ...c, ...Object.fromEntries(fresh.map((k) => [k, stamp])) }));
    const t = setTimeout(
      () => setCallbacks((c) => Object.fromEntries(Object.entries(c).filter(([, v]) => v !== stamp))),
      2200,
    );
    return () => clearTimeout(t);
  }, [model.pipeline]);

  const anyWorking = PIPELINE_AGENTS.some((a) => model.pipeline[a.key].status === "working");

  const renderNode = (key: AgentKey) => {
    const info = PIPELINE_AGENTS.find((a) => a.key === key)!;
    const node = model.pipeline[key];
    const live = animated && node.status === "working";
    const flash = animated && callbacks[key] !== undefined;
    const notCalled = key in skipped && node.status === "idle";
    return (
      <div key={key} className={`${styles.col} ${styles[node.status]} ${notCalled ? styles.notCalled : ""}`}>
        <div className={styles.wire} aria-hidden>
          {live && <span className={styles.packetDown} />}
          {flash && <span key={callbacks[key]} className={styles.packetUp} />}
        </div>
        <motion.div
          className={`${styles.node} ${live ? styles.nodeLive : ""}`}
          animate={flash ? { scale: [1, 1.05, 1] } : { scale: 1 }}
          transition={{ duration: 0.6 }}
        >
          <div className={styles.nodeTop}>
            <span className={styles.dot} />
            <span className={styles.name}>{info.name}</span>
          </div>
          <div className={styles.state}>
            {notCalled ? "not called" : STATE_WORD[node.status]}
            {live && (
              <span className={styles.typing} aria-hidden>
                <i />
                <i />
                <i />
              </span>
            )}
            <AnimatePresence>
              {node.status === "reported" && (
                <motion.span
                  className={styles.tick}
                  initial={{ scale: 0, rotate: -40 }}
                  animate={{ scale: 1, rotate: 0 }}
                  transition={{ type: "spring", stiffness: 420, damping: 16 }}
                >
                  ✓
                </motion.span>
              )}
            </AnimatePresence>
          </div>
          <div className={styles.note}>{notCalled ? skipped[key] : node.note ?? info.role}</div>
        </motion.div>
      </div>
    );
  };

  return (
    <div className={styles.flow}>
      <div className={`${styles.manager} ${animated && anyWorking ? styles.managerLive : ""}`}>
        <div className={styles.managerTitle}>Incident Manager</div>
        <div className={styles.managerSub}>
          sends every request to the agents below over A2A, and collects every reply
        </div>
        <div className={styles.managerLatest} aria-live="polite">
          <motion.span
            key={model.latest?.id ?? "none"}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25 }}
          >
            {model.latest ? `now: ${model.latest.label} — ${model.latest.actor}` : "waiting for the first event"}
          </motion.span>
        </div>
      </div>

      <div className={styles.rowLabel}>Step 1 · four investigators gather evidence at the same time</div>
      <div className={styles.row4}>{INVESTIGATORS.map(renderNode)}</div>

      <div className={styles.rowLabel}>Step 2 · combine, challenge, then propose a fix</div>
      <div className={styles.row3}>{REASONERS.map(renderNode)}</div>
    </div>
  );
}
