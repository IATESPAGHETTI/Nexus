import { useEffect, useMemo, useRef } from "react";
import { motion } from "motion/react";
import type { NexusEvent } from "../../api/types";
import { buildConversation, type ConversationRow } from "../../lib/conversation";
import { PIPELINE_AGENTS, type CommandCenterModel } from "../../lib/presentation";
import styles from "./AgentConversation.module.css";

interface Props {
  events: NexusEvent[] | undefined;
  model: CommandCenterModel;
  animated: boolean;
}

function clock(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? "" : d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function Row({ row, index }: { row: ConversationRow; index: number }) {
  if (row.kind === "round") {
    return (
      <motion.li
        className={styles.round}
        initial={{ opacity: 0, scaleX: 0.9 }}
        animate={{ opacity: 1, scaleX: 1 }}
        transition={{ duration: 0.3, delay: Math.min(index * 0.02, 0.3) }}
      >
        <span>{row.said}</span>
      </motion.li>
    );
  }
  return (
    <motion.li
      className={styles.row}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: Math.min(index * 0.02, 0.3) }}
    >
      <div className={styles.meta}>
        <span className={styles.time}>{clock(row.time)}</span>
        <span className={styles.route}>
          <b>{row.from}</b> <span className={styles.arrow}>→</span> <b>{row.to}</b>
        </span>
        {row.taskId && <span className={styles.task}>task {row.taskId.slice(0, 8)}</span>}
      </div>
      <div className={`${styles.bubble} ${styles[`k_${row.kind}`]}`}>
        <span className={styles.tag}>{row.kind === "exchange" ? "REQUEST" : row.kind === "triage" ? "TRIAGE" : row.kind === "human" ? "PERSON" : row.kind === "guardrail" ? "SAFETY" : "MESSAGE"}</span>
        {row.said}
      </div>
      {row.reply && (
        <div className={`${styles.bubble} ${styles.reply} ${row.replyFailed ? styles.replyFailed : ""}`}>
          <span className={styles.tag}>{row.replyFailed ? "PROBLEM" : "CALLBACK"}</span>
          <span className={styles.from}>{row.kind === "exchange" ? `${row.to} → ${row.from}: ` : ""}</span>
          {row.reply}
        </div>
      )}
    </motion.li>
  );
}

/**
 * The visible “agent callbacks”: every request the Incident Manager sent over
 * A2A and the reply that came back, in order, built from the real event log.
 * Agents that have been asked but not yet answered show a live waiting line.
 */
export function AgentConversation({ events, model, animated }: Props) {
  const rows = useMemo(() => buildConversation(events), [events]);
  const listRef = useRef<HTMLOListElement>(null);
  const seen = useRef(0);

  // follow new messages, like a chat, but only when the list grows
  useEffect(() => {
    if (rows.length > seen.current && listRef.current) {
      listRef.current.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" });
    }
    seen.current = rows.length;
  }, [rows.length]);

  const waiting = animated
    ? PIPELINE_AGENTS.filter((a) => model.pipeline[a.key].status === "working")
    : [];

  return (
    <div className={styles.wrap}>
      <div className={styles.head}>
        <span className={styles.title}>Agent conversation</span>
        <span className={styles.sub}>who asked whom, and what came back · {rows.length} messages</span>
      </div>
      {rows.length === 0 && waiting.length === 0 ? (
        <p className={styles.empty}>No messages yet. They appear here the moment the Incident Manager contacts an agent.</p>
      ) : (
        <ol className={styles.list} ref={listRef}>
          {rows.map((r, i) => (
            <Row key={r.id} row={r} index={i} />
          ))}
          {waiting.map((a) => (
            <li key={`wait-${a.key}`} className={styles.waiting}>
              <span className={styles.typing} aria-hidden>
                <i />
                <i />
                <i />
              </span>
              <span>
                <b>Incident Manager</b> asked <b>{a.name}</b>, waiting for the reply…
              </span>
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}
