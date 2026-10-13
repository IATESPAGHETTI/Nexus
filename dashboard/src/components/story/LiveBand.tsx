import { motion } from "motion/react";
import { AgentMasterToggle } from "../common/AgentMasterToggle";
import { LivePipelineSection } from "../presentation/LivePipelineSection";
import { LiveIncidentCommandCenter } from "../command_center/LiveIncidentCommandCenter";
import { SectionMarker } from "./StorySections";
import styles from "./LiveBand.module.css";

const EASE = [0.16, 1, 0.3, 1] as const;

/**
 * Full-bleed light band matching the rest of the page. Everything inside reads real backend state (or says it can't).
 */
export function LiveBand({ withPipeline = true }: { withPipeline?: boolean }) {
  return (
    <section id="pl-live" className={styles.band}>
      <div className={styles.inner}>
        <SectionMarker label="The live system" />
        <motion.h2
          className={styles.title}
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: "-80px" }}
          transition={{ duration: 0.7, ease: EASE }}
        >
          Turn the agents on and watch a real investigation.
        </motion.h2>
        <p className={styles.sub}>
          With agents OFF nothing below is live, and nothing runs in the background. With agents ON, every status, event and
          finding is read from the real backend.
        </p>

        <div className={styles.switchRow}>
          <AgentMasterToggle />
          <ul className={styles.legend}>
            <li>
              <i className={styles.dOff} />
              <b>Agents OFF</b> Illustrative walkthrough only. No incident, no numbers.
            </li>
            <li>
              <i className={styles.dOn} />
              <b>ON, backend live</b> Real incident data, real agent events, real tool calls.
            </li>
            <li>
              <i className={styles.dWarn} />
              <b>ON, backend unreachable</b> Shown as such. Nothing is substituted.
            </li>
          </ul>
        </div>
      </div>

      {withPipeline && <LivePipelineSection />}
      <LiveIncidentCommandCenter />
    </section>
  );
}
