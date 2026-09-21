import { motion } from "motion/react";
import { SectionMarker } from "./StorySections";
import styles from "./Bento.module.css";

const EASE = [0.16, 1, 0.3, 1] as const;

interface CardProps {
  className?: string;
  title: string;
  role: string;
  analogy: string;
  text: string;
  lines: string[];
  index: number;
  children?: React.ReactNode;
}

function Arrow() {
  return (
    <svg className={styles.arrow} width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M7 17 17 7M8 7h9v9" />
    </svg>
  );
}

/** Dark "product" panel with mono lines — names of real tools / enums only, never results. */
function Vis({ lines }: { lines: string[] }) {
  return (
    <div className={styles.vis}>
      <div className={styles.glow} />
      {lines.map((l, i) => (
        <div key={i} className={styles.visLine} style={{ animationDelay: `${i * 0.35}s` }}>
          <span className={styles.prompt}>›</span> {l}
        </div>
      ))}
    </div>
  );
}

function Card({ className = "", title, role, analogy, text, lines, index, children }: CardProps) {
  return (
    <motion.article
      className={`${styles.card} ${className}`}
      initial={{ opacity: 0, y: 36 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-70px" }}
      transition={{ duration: 0.7, ease: EASE, delay: index * 0.08 }}
    >
      <Arrow />
      <div className={styles.copy}>
        <div className={styles.role}>{role}</div>
        <h3 className={styles.name}>{title}</h3>
        <p className={styles.text}>{text}</p>
        <p className={styles.analogy}>
          <b>Hospital analogy</b> {analogy}
        </p>
      </div>
      {children}
      <Vis lines={lines} />
    </motion.article>
  );
}

export function AgentBento() {
  return (
    <section id="pl-agents" className={styles.section}>
      <div className={styles.container}>
        <SectionMarker label="The agent team" />
        <motion.h2
          className={styles.title}
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.7, ease: EASE }}
        >
          Seven agents. One coordinated investigation.
          <span> Each has a single, bounded job, like a hospital team.</span>
        </motion.h2>

        <div className={styles.grid}>
          <Card
            index={0}
            className={styles.wide}
            role="Four diagnostic agents · in parallel"
            title="Gather the evidence"
            text="Metrics checks system vitals. Logs & Traces checks symptoms and request behaviour. Change Analysis checks what recently changed. Database checks database health. Each reaches the system only through read-only MCP tools."
            analogy="nurse, patient-history reviewer, pharmacist and lab technician."
            lines={["metrics_agent → get_metrics", "logs_traces_agent → query_logs, get_trace", "change_analysis_agent → get_recent_deployments, get_git_diff", "database_agent → get_database_stats"]}
          />
          <Card
            index={1}
            role="Evidence Agent"
            title="Form possible causes"
            text="Combines the four reports into hypotheses, each with evidence for it, evidence against it, and what is still missing."
            analogy="the senior physician."
            lines={["supporting_evidence_ids", "contradicting_evidence_ids", "missing_evidence"]}
          />
          <Card
            index={2}
            className={styles.half}
            role="Root-Cause Critic"
            title="Try to prove it wrong"
            text="Looks for contradictions and unsupported assumptions, asks for more evidence, and can send the loop round again. It may conclude that the cause is not proven."
            analogy="the second opinion."
            lines={["SUPPORTED", "INSUFFICIENT_EVIDENCE", "CONTRADICTED", "REQUEST_MORE_EVIDENCE"]}
          />
          <Card
            index={3}
            className={styles.half}
            role="Recovery Agent"
            title="Propose, never execute"
            text="Drafts a bounded plan from a short allow-list. It cannot run anything itself: guardrails validate the plan, and it runs only after a person approves."
            analogy="the treatment team, acting only after consent."
            lines={["restart_service", "rollback_deployment", "reset_config", "scale_resources"]}
          />
        </div>
      </div>
    </section>
  );
}
