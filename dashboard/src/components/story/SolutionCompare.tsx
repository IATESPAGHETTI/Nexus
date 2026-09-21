import { motion } from "motion/react";
import { SectionMarker } from "./StorySections";
import styles from "./Compare.module.css";

const EASE = [0.16, 1, 0.3, 1] as const;

// Stagger each message into its window as the section scrolls into view.
function Msg({ i, children, className = "" }: { i: number; children: React.ReactNode; className?: string }) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.5, ease: EASE, delay: 0.25 + i * 0.16 }}
    >
      {children}
    </motion.div>
  );
}

function Pill({ action, target }: { action: string; target: string }) {
  return (
    <div className={styles.pill}>
      <span className={styles.pillDot} />
      <span className={styles.pillAction}>{action}</span>
      <span className={styles.pillTarget}>{target}</span>
    </div>
  );
}

function WindowBar({ title, badge }: { title: string; badge?: string }) {
  return (
    <div className={styles.bar}>
      <span className={styles.dots}>
        <i className={styles.r} />
        <i className={styles.y} />
        <i className={styles.g} />
      </span>
      <span className={styles.barTitle}>{title}</span>
      {badge && <span className={styles.badge}>{badge}</span>}
    </div>
  );
}

const ASK = "Customers say order requests are slow. What is the cause?";

export function SolutionCompare() {
  return (
    <section id="pl-solution" className={styles.section}>
      <div className={styles.aurora} aria-hidden="true" />
      <div className={styles.container}>
        <SectionMarker label="The solution" />
        <div className={styles.head}>
          <motion.h2
            className={styles.title}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.7, ease: EASE }}
          >
            Evidence first. Challenge before acting.
          </motion.h2>
          <p className={styles.sub}>
            Four agents read real diagnostic tools, a fifth turns their findings into possible causes, a critic tries to knock the
            leading one down, and a person approves any fix. <strong>Same failure, a very different process.</strong>
          </p>
          <p className={styles.note}>Illustrative comparison of the two designs. It is not a recorded run.</p>
        </div>

        <div className={styles.grid}>
          {/* ---- one model, one pass ---- */}
          <div className={styles.pane}>
            <WindowBar title="One model, one pass" />
            <div className={styles.body}>
              <Msg i={0} className={styles.user}>{ASK}</Msg>
              <Msg i={1}>
                <Pill action="read" target="one flat snapshot: metrics, logs, changes, database" />
              </Msg>
              <Msg i={2} className={styles.text}>
                Picks a cause from a fixed list in a single call.
              </Msg>
            </div>
            <div className={styles.miss}>
              <div className={styles.missTitle}>What this design cannot do</div>
              {[
                ["Gather more evidence", "one read, one answer"],
                ["Get a second opinion", "there is no critic"],
                ["Stop before acting", "recovery is not part of it"],
              ].map(([a, b], i) => (
                <Msg key={a} i={3 + i} className={styles.missRow}>
                  <span className={styles.x}>×</span>
                  <b>{a}</b> <span>{b}</span>
                </Msg>
              ))}
            </div>
          </div>

          {/* ---- NEXUS ---- */}
          <div className={styles.pane}>
            <WindowBar title="NEXUS" badge="7 agents · MCP + A2A" />
            <div className={styles.body}>
              <Msg i={0} className={styles.user}>{ASK}</Msg>
              <Msg i={1}>
                <div className={styles.stack}>
                  <Pill action="metrics_agent" target="get_metrics" />
                  <Pill action="logs_traces_agent" target="query_logs · get_trace" />
                  <Pill action="change_analysis_agent" target="get_recent_deployments" />
                  <Pill action="database_agent" target="get_database_stats" />
                </div>
              </Msg>
              <Msg i={2} className={styles.text}>
                The Evidence Agent proposes possible causes, each linked to its supporting and contradicting evidence.
              </Msg>
              <Msg i={3}>
                <div className={styles.card}>
                  <div className={styles.cardHead}>
                    <span className={styles.pillDot} />
                    <span className={styles.pillAction}>root_cause_critic</span>
                    <span className={styles.pillTarget}>challenges the leading cause</span>
                  </div>
                  <div className={styles.verdicts}>
                    <span>SUPPORTED</span>
                    <span>NOT PROVEN</span>
                    <span>CONTRADICTED</span>
                  </div>
                </div>
              </Msg>
              <Msg i={4}>
                <div className={styles.card}>
                  <div className={styles.cardHead}>
                    <span className={styles.pillDot} />
                    <span className={styles.pillAction}>recovery</span>
                    <span className={styles.pillTarget}>bounded, and gated</span>
                  </div>
                  <ol className={styles.plan}>
                    <li>Agent proposes a plan from a short allow-list</li>
                    <li>Guardrails validate it independently</li>
                    <li>A person approves before anything runs</li>
                  </ol>
                </div>
              </Msg>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
