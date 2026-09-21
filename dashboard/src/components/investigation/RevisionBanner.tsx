import { motion, AnimatePresence } from "motion/react";
import { GlassSurface } from "../primitives/GlassSurface";
import { Badge } from "../primitives/Badge";
import { MonoLabel } from "../primitives/MonoLabel";
import { ConfidenceBar } from "../primitives/ConfidenceBar";
import { hypothesisStatusTone, verdictTone } from "../primitives/semantics";
import type { Critique, Hypothesis } from "../../api/types";
import styles from "./RevisionBanner.module.css";

// Note: agents/evidence/agent.py's `revision` field is fixed at 1 and
// hypothesis_ids are reassigned fresh on every re-investigation round (see
// docs/PROJECT_STATE.md / orchestrator/investigation.py) — there is no
// same-hypothesis confidence-delta signal in the real data today. This banner
// shows the real signal that does exist: the critic's actual verdict
// transition and cited contradictions for this hypothesis, in place of a
// fabricated "78% -> 41%" delta.
export function RevisionBanner({
  hypothesis,
  critique,
}: {
  hypothesis: Hypothesis;
  critique: Critique | undefined;
}) {
  const revised = hypothesis.status !== "PROPOSED" && critique;

  return (
    <AnimatePresence>
      {revised && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0 }}
          transition={{ type: "spring", stiffness: 280, damping: 30 }}
        >
          <GlassSurface className={styles.banner}>
            <div className={styles.heading}>Hypothesis revised</div>
            <div className={styles.transition}>
              <Badge tone="neutral">PROPOSED</Badge>
              <span style={{ color: "var(--nx-ink-4)" }}>&rarr;</span>
              <Badge tone={hypothesisStatusTone(hypothesis.status)}>{hypothesis.status}</Badge>
              <span style={{ marginLeft: "auto", width: 120 }}>
                <ConfidenceBar
                  value={hypothesis.confidence}
                  compact
                  tone={hypothesisStatusTone(hypothesis.status)}
                />
              </span>
            </div>
            {critique && (
              <>
                <div className={styles.rationale}>
                  <Badge tone={verdictTone(critique.verdict)}>{critique.verdict}</Badge>
                  {"  "}
                  {critique.rationale}
                </div>
                {(critique.contradictions ?? []).length > 0 && (
                  <div className={styles.list}>
                    {(critique.contradictions ?? []).map((c, i) => (
                      <div key={i} className={styles.listItem}>
                        <MonoLabel>&#8212;</MonoLabel> {c}
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </GlassSurface>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
