import { motion } from "motion/react";
import { SectionMarker } from "./StorySections";
import styles from "./Fixes.module.css";

const EASE = [0.16, 1, 0.3, 1] as const;

// Every item is a problem we actually hit while running NEXUS against the simulated shop, and the
// change that fixed it. The three "found by reading abstained runs" items come from the practice
// runs recorded in docs/PROJECT_STATE.md.
const FIXES: { problem: string; fix: string; tag: string }[] = [
  {
    tag: "Cheating",
    problem: "An agent could read the project's own code history, which names the injected failure. That is like seeing the answer key.",
    fix: "That tool is switched off by default, and the Change Analysis agent no longer has it. A scan of later runs found no leaked hints.",
  },
  {
    tag: "Blind spot",
    problem: "When requests failed, the shop's logs only said “500 error”. The real message, such as an invalid setting, was never recorded, so agents had to guess.",
    fix: "The shop now writes the error message into its logs, as a real application does. Wrong-setting runs went from guessing to fixing.",
  },
  {
    tag: "Wrong fix",
    problem: "In one run the plan was “restart the service” for a problem a restart cannot fix. A person approved it and the shop stayed broken.",
    fix: "A safety check with no AI in it now rejects any plan whose actions cannot fix the recognised symptom. The live check also refused to call the broken shop recovered.",
  },
  {
    tag: "False alarm",
    problem: "After a correct fix, NEXUS reported “not verified”. The check itself was slow because of how the laptop looked up its own address.",
    fix: "The check now uses the direct address, so a healthy shop is measured in about 10 ms instead of 2 seconds.",
  },
  {
    tag: "Impossible asks",
    problem: "The Critic kept demanding evidence no tool can provide, such as the payment service's own health, so it never became satisfied and NEXUS gave up.",
    fix: "It is now told exactly what evidence can exist. It accepts a diagnosis when sources agree and nothing contradicts it.",
  },
  {
    tag: "Runaway cost",
    problem: "One agent kept calling tools and used 95,000 tokens in a single run, past its limit.",
    fix: "The limit did its job and stopped it. The Logs agent is now capped at four tool calls, and the usage panel shows real spend against the limits.",
  },
  {
    tag: "Dirty test",
    problem: "Leftovers of an earlier failure, such as old errors and old rollbacks, stayed in the shop and looked like evidence in the next one.",
    fix: "The shop has a reset. Each demo and each test run now starts from a clean shop.",
  },
  {
    tag: "Lost work",
    problem: "Incidents lived in memory, so a restart erased them. If the approval window passed, the saved plan could not be used.",
    fix: "Incidents are stored in a database and survive restarts. An expired plan can still be approved later, and it is re-checked before it runs.",
  },
];

export function FixesSection() {
  return (
    <section id="pl-fixes" className={styles.section}>
      <div className={styles.container}>
        <SectionMarker label="What testing taught us" />
        <motion.h2
          className={styles.title}
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.7, ease: EASE }}
        >
          We broke it, watched it fail, and fixed what we found. <span>Eight real problems, none hidden.</span>
        </motion.h2>
        <p className={styles.lead}>
          Running NEXUS against the five failures exposed real weaknesses, some in the AI and some in our own setup. Each one
          below was found by reading what actually happened, not by guessing, and each fix was re-tested.
        </p>

        <div className={styles.grid}>
          {FIXES.map((f, i) => (
            <motion.article
              key={f.tag}
              className={styles.card}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-40px" }}
              transition={{ duration: 0.5, ease: EASE, delay: (i % 2) * 0.06 }}
            >
              <div className={styles.cardTop}>
                <span className={styles.num}>0{i + 1}</span>
                <span className={styles.tag}>{f.tag}</span>
              </div>
              <div className={styles.row}>
                <span className={styles.label}>What went wrong</span>
                <p>{f.problem}</p>
              </div>
              <div className={`${styles.row} ${styles.fixRow}`}>
                <span className={styles.label}>The fix</span>
                <p>{f.fix}</p>
              </div>
            </motion.article>
          ))}
        </div>

        <div className={styles.note}>
          <b>An honest limit.</b> After these fixes all five failures were diagnosed, repaired and verified, but each was run
          once. That is a smoke test, not a benchmark. Two of the prompt changes were made after seeing these same failures,
          so a fair accuracy number needs new scenarios the system has never seen.
        </div>
      </div>
    </section>
  );
}
