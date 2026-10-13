import { motion } from "motion/react";
import { DEMO_SCENARIOS } from "../../lib/scenarios";
import { SectionMarker } from "./StorySections";
import styles from "./Failures.module.css";

const EASE = [0.16, 1, 0.3, 1] as const;

// What each injected failure breaks, the clue the agents read, and the fix NEXUS may propose.
// "Called first" is what the Incident Manager's triage picked in our practice runs (one run each,
// not a benchmark); the live dashboard shows the real choice for every incident.
const DETAIL: Record<string, { part: string; clue: string; fix: string; called: string[] }> = {
  db_slowdown: {
    part: "Database",
    clue: "Database queries take about 260 ms on a tiny table, while nothing errors.",
    fix: "Restore service resources",
    called: ["Metrics", "Logs & Traces", "Database"],
  },
  bad_deployment: {
    part: "Deployed code",
    clue: "A new version appears in the change history just before the errors start.",
    fix: "Roll back to the previous version",
    called: ["Metrics", "Logs & Traces", "Change Analysis"],
  },
  config_error: {
    part: "Configuration",
    clue: "The error log names an invalid setting (a pool size of 0).",
    fix: "Reset configuration to its known-good values",
    called: ["Metrics", "Logs & Traces"],
  },
  dependency_failure: {
    part: "Outside service",
    clue: "Logs show timeouts reaching the payment service, only on single-order lookups.",
    fix: "Restart the service",
    called: ["Metrics", "Logs & Traces"],
  },
  resource_exhaustion: {
    part: "Server resources",
    clue: "Every page slows down and some are refused, with a memory-limit error in the logs.",
    fix: "Restore service resources",
    called: ["Metrics", "Logs & Traces", "Database"],
  },
};

export function FailuresSection() {
  return (
    <section id="pl-failures" className={styles.section}>
      <div className={styles.container}>
        <SectionMarker label="What we break on purpose" />
        <motion.h2
          className={styles.title}
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.7, ease: EASE }}
        >
          Five ways the shop breaks. <span>NEXUS only hears what a customer would say.</span>
        </motion.h2>
        <p className={styles.lead}>
          The test target is a simulated online shop: an API, a database behind it, settings, and a deployed version. We
          break one part at a time. NEXUS is never told the cause. It gets a customer-style complaint, then has to find the
          cause from evidence, propose a fix from a short safe list, and wait for a person to approve it.
        </p>

        <div className={styles.grid}>
          {DEMO_SCENARIOS.map((sc, i) => {
            const d = DETAIL[sc.id];
            return (
              <motion.article
                key={sc.id}
                className={styles.card}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{ duration: 0.5, ease: EASE, delay: i * 0.05 }}
              >
                <div className={styles.cardTop}>
                  <span className={styles.num}>0{i + 1}</span>
                  <span className={styles.part}>{d.part}</span>
                </div>
                <h3 className={styles.name}>{sc.label}</h3>
                <p className={styles.blurb}>{sc.blurb}</p>
                <dl className={styles.facts}>
                  <div>
                    <dt>The customer says</dt>
                    <dd>“{sc.symptom.replace(" Investigate the cause.", "")}”</dd>
                  </div>
                  <div>
                    <dt>The clue agents find</dt>
                    <dd>{d.clue}</dd>
                  </div>
                  <div>
                    <dt>The fix it proposes</dt>
                    <dd>{d.fix}</dd>
                  </div>
                </dl>
                <div className={styles.called}>
                  <span className={styles.calledLabel}>Agents called first</span>
                  <span className={styles.chips}>
                    {d.called.map((c) => (
                      <i key={c}>{c}</i>
                    ))}
                  </span>
                </div>
              </motion.article>
            );
          })}
        </div>

        <div className={styles.note}>
          <b>Not every agent is called every time.</b> Like an on-call lead deciding who to page, the Incident Manager reads
          the complaint and calls only the specialists it points at. If the Critic later asks for something a skipped agent
          covers, that agent is called in the next round. The live dashboard shows who was called, who was skipped, and why.
        </div>
      </div>
    </section>
  );
}
