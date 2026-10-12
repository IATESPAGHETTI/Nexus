import { useEffect, useRef, useState } from "react";
import { motion, useMotionValueEvent, useScroll } from "motion/react";
import styles from "./Story.module.css";

const EASE = [0.16, 1, 0.3, 1] as const;

export function SectionMarker({ label, dark = false }: { label: string; dark?: boolean }) {
  return (
    <motion.div
      className={`${styles.marker} ${dark ? styles.markerDark : ""}`}
      initial="hidden"
      whileInView="shown"
      viewport={{ once: true, margin: "-60px" }}
    >
      <motion.span
        className={styles.markerLabel}
        variants={{ hidden: { opacity: 0, x: -12 }, shown: { opacity: 1, x: 0 } }}
        transition={{ duration: 0.5, ease: EASE }}
      >
        {label}
      </motion.span>
      <motion.span
        className={styles.markerLine}
        variants={{ hidden: { scaleX: 0 }, shown: { scaleX: 1 } }}
        transition={{ duration: 0.9, ease: EASE, delay: 0.1 }}
      />
    </motion.div>
  );
}

// Real technologies NEXUS is built on (names only; no logos are used).
const STACK: [string, string][] = [
  ["Model Context Protocol", "diagnostic tools"],
  ["Agent2Agent", "agent-to-agent calls"],
  ["Google ADK", "agent framework"],
  ["LiteLLM", "model gateway"],
  ["DeepSeek", "runtime model"],
  ["FastAPI", "backend"],
  ["React", "dashboard"],
  ["Docker Compose", "deployment"],
];

export function TechMarquee() {
  const items = [...STACK, ...STACK];
  return (
    <section className={styles.marqueeSection}>
      <p className={styles.marqueeHeading}>Built on real protocols and open tooling</p>
      <div className={styles.marqueeWrap}>
        <div className={styles.marqueeTrack}>
          {items.map(([name, role], i) => (
            <span key={i} className={styles.marqueeItem} aria-hidden={i >= STACK.length}>
              {name}
              <small>{role}</small>
            </span>
          ))}
        </div>
      </div>
    </section>
  );
}

const SIGNALS: [string, string][] = [
  ["Metrics", "latency, errors"],
  ["Logs", "what each request said"],
  ["Traces", "where time went"],
  ["Deployments", "what changed"],
  ["Database", "what the queries did"],
];

export function ProblemSection() {
  return (
    <section id="pl-problem" className={styles.problem}>
      <div className={styles.container}>
        <SectionMarker label="The problem" />
        <div className={styles.problemGrid}>
          <motion.h2
            className={styles.problemHeadline}
            initial={{ opacity: 0, y: 28 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.7, ease: EASE }}
          >
            When production breaks, the hard part is finding out why.
            <span className={styles.problemSecondary}>
              Metrics, logs, deployments and the database each tell part of the story, and they rarely agree until someone connects them.
            </span>
          </motion.h2>
          <ul className={styles.signals}>
            {SIGNALS.map(([name, hint], i) => (
              <motion.li
                key={name}
                className={styles.signal}
                initial={{ opacity: 0, x: 24 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: "-40px" }}
                transition={{ duration: 0.5, ease: EASE, delay: i * 0.08 }}
              >
                <span className={styles.signalN}>0{i + 1}</span>
                {name}
                <span className={styles.signalHint}>{hint}</span>
              </motion.li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

const STATEMENT =
  "A single model reading a description is guessing. NEXUS sends specialist agents to collect evidence, makes them argue about what it means, and declines to answer when the evidence is not enough. Then it asks a person before it touches anything.".split(
    " ",
  );

/** Words fill from grey to black as the card scrolls through the viewport. */
export function StatementReveal() {
  const ref = useRef<HTMLDivElement>(null);
  const [filled, setFilled] = useState(0);
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start 80%", "end 45%"] });
  useMotionValueEvent(scrollYProgress, "change", (v) => {
    const n = Math.round(Math.min(1, Math.max(0, v)) * STATEMENT.length);
    setFilled((prev) => (prev === n ? prev : n));
  });
  return (
    <section className={styles.statementSection}>
      <div className={styles.container}>
        <div ref={ref} className={styles.statementCard}>
          <p className={styles.statementText}>
            {STATEMENT.map((w, i) => (
              <span key={i} className={`${styles.word} ${i < filled ? styles.wordFilled : ""}`}>
                {w}{" "}
              </span>
            ))}
          </p>
        </div>
      </div>
    </section>
  );
}

const STEPS: [string, string][] = [
  ["Detect", "An incident is opened. In the demo, a controlled fault is injected into the simulated order service. NEXUS does not watch production on its own yet."],
  ["Investigate", "Four specialist agents run read-only diagnostic tools and each reports what it actually saw."],
  ["Understand", "The Evidence Agent turns those reports into possible causes, each tied to the evidence for and against it."],
  ["Challenge", "The Root-Cause Critic looks for contradictions. If the cause cannot be proven, NEXUS abstains instead of guessing."],
  ["Recover", "A bounded plan is proposed from a short allow-list, validated by guardrails, and run only after a person approves."],
  ["Verify", "The Metrics Agent checks the service again. The incident is resolved only if that check confirms recovery."],
];

export function StepsRail() {
  return (
    <section className={styles.steps}>
      <div className={styles.container}>
        <SectionMarker label="How an investigation runs" />
        <h2 className={styles.stepsTitle}>
          Detect, investigate, understand, challenge, recover, verify. <span>Every step leaves evidence behind.</span>
        </h2>
        <div className={styles.stepsGrid}>
          {STEPS.map(([name, text], i) => (
            <motion.div
              key={name}
              className={`${styles.step}`}
              initial="out"
              whileInView="in"
              viewport={{ once: true, margin: "-60px" }}
              transition={{ delay: i * 0.12 }}
            >
              <StepBar />
              <div className={styles.stepN}>0{i + 1}</div>
              <h3 className={styles.stepName}>{name}</h3>
              <p className={styles.stepText}>{text}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// The rail's coloured top edge draws in when the step scrolls into view.
function StepBar() {
  return (
    <motion.span
      aria-hidden="true"
      style={{ position: "absolute", top: -1, left: 0, height: 2, background: "var(--lt-brand)", transformOrigin: "left" }}
      variants={{ out: { width: "0%" }, in: { width: "100%" } }}
      transition={{ duration: 0.8, ease: EASE }}
    />
  );
}

export function FinalCta({ onClick }: { onClick: () => void }) {
  return (
    <>
      <section className={styles.cta}>
        <div className={styles.container}>
          <motion.h2
            className={styles.ctaTitle}
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-80px" }}
            transition={{ duration: 0.7, ease: EASE }}
          >
            See NEXUS investigate a real failure.
          </motion.h2>
          <p className={styles.ctaSub}>
            Turn the agents on, inject a database slowdown, and watch seven agents work from real evidence.
          </p>
          <button type="button" className={styles.ctaBtn} onClick={onClick}>
            Open the live system
          </button>
        </div>
      </section>
      <footer className={styles.footer}>
        NEXUS · Autonomous Multi-Agent Production Failure Investigation &amp; Recovery
        <br />
        Live views read only real backend state · Recovery requires human approval
      </footer>
    </>
  );
}

const PILLARS: [string, string][] = [
  ["pl-problem", "Problem"],
  ["pl-solution", "Solution"],
  ["pl-agents", "Agents"],
  ["pl-architecture", "Architecture"],
  ["pl-failures", "Failures"],
  ["pl-fixes", "Fixes"],
  ["pl-live", "Live system"],
];

export function PillarsNav() {
  const [visible, setVisible] = useState(false);
  const [active, setActive] = useState<string>("");

  useEffect(() => {
    const onScroll = () => {
      const first = document.getElementById("pl-problem");
      setVisible(first ? first.getBoundingClientRect().top < window.innerHeight * 0.7 : false);
      let current = "";
      for (const [id] of PILLARS) {
        const el = document.getElementById(id);
        if (el && el.getBoundingClientRect().top < window.innerHeight * 0.45) current = id;
      }
      setActive(current);
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <nav className={`${styles.pillars} ${visible ? styles.pillarsVisible : ""}`} aria-label="Sections">
      {PILLARS.map(([id, label]) => (
        <button
          key={id}
          type="button"
          className={`${styles.pillar} ${active === id ? styles.pillarActive : ""}`}
          onClick={() => document.getElementById(id)?.scrollIntoView({ behavior: "smooth" })}
        >
          <span className={styles.pillarDot} />
          {label}
        </button>
      ))}
    </nav>
  );
}
