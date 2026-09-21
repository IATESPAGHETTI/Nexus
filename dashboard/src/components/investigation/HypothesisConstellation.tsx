import { AnimatePresence, motion } from "motion/react";
import { GlassSurface } from "../primitives/GlassSurface";
import { ConfidenceBar } from "../primitives/ConfidenceBar";
import { Badge } from "../primitives/Badge";
import { hypothesisStatusTone } from "../primitives/semantics";
import { EvidenceNode } from "./EvidenceNode";
import type { EvidenceLookupEntry } from "../../lib/derive";
import type { Hypothesis } from "../../api/types";
import styles from "./HypothesisConstellation.module.css";

interface HypothesisConstellationProps {
  hypothesis: Hypothesis;
  evidenceLookup: Record<string, EvidenceLookupEntry>;
}

export function HypothesisConstellation({ hypothesis, evidenceLookup }: HypothesisConstellationProps) {
  return (
    <div className={styles.wrap}>
      <div className={styles.stage}>
        <div className={`${styles.side} ${styles.sideLeft}`}>
          <span className={`${styles.caption} ${styles.captionLeft}`}>Supporting</span>
          <AnimatePresence initial={false}>
            {hypothesis.supporting_evidence_ids.length === 0 && (
              <span className={styles.emptySide}>none yet</span>
            )}
            {hypothesis.supporting_evidence_ids.map((id, i) => (
              <EvidenceNode key={id} evidenceId={id} entry={evidenceLookup[id]} side="left" index={i} />
            ))}
          </AnimatePresence>
        </div>

        <motion.div layout transition={{ type: "spring", stiffness: 260, damping: 30 }}>
          <GlassSurface elevation="raised" className={styles.center}>
            <Badge tone={hypothesisStatusTone(hypothesis.status)}>{hypothesis.status}</Badge>
            <div className={styles.statement}>{hypothesis.statement}</div>
            <ConfidenceBar value={hypothesis.confidence} tone={hypothesisStatusTone(hypothesis.status)} />
          </GlassSurface>
        </motion.div>

        <div className={`${styles.side} ${styles.sideRight}`}>
          <span className={styles.caption}>Contradicting</span>
          <AnimatePresence initial={false}>
            {hypothesis.contradicting_evidence_ids.length === 0 && (
              <span className={styles.emptySide}>none yet</span>
            )}
            {hypothesis.contradicting_evidence_ids.map((id, i) => (
              <EvidenceNode key={id} evidenceId={id} entry={evidenceLookup[id]} side="right" index={i} />
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
