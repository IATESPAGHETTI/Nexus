import { GlassSurface } from "../primitives/GlassSurface";
import { Badge } from "../primitives/Badge";
import { MonoLabel } from "../primitives/MonoLabel";
import { verdictTone } from "../primitives/semantics";
import type { Critique } from "../../api/types";
import styles from "./CriticChallengePanel.module.css";

export function CriticChallengePanel({ critiques }: { critiques: Critique[] }) {
  return (
    <GlassSurface className={styles.wrap}>
      <div className={styles.title} title="Challenges hypotheses against available evidence before diagnosis.">
        Root-Cause Critic
      </div>
      {critiques.length === 0 ? (
        <div className={styles.empty}>No critique issued yet.</div>
      ) : (
        critiques
          .slice()
          .reverse()
          .map((c, i) => {
            // orchestrator/investigation.py falls back to a minimal critique
            // object (verdict + rationale only) when the Critic's real A2A
            // response is unparseable (e.g. under Groq rate-limit pressure) —
            // the fuller Critique shape from agents/critic/agent.py's
            // build_critique() is not guaranteed in that real fallback path,
            // so every optional array here is read defensively.
            const requestedEvidence = c.requested_evidence ?? [];
            const alternativeExplanations = c.alternative_explanations ?? [];
            return (
              <div className={styles.card} key={c.critique_id ?? `${c.hypothesis_id}-${i}`}>
                <div className={styles.cardHead}>
                  <MonoLabel>{c.hypothesis_id}</MonoLabel>
                  <Badge tone={verdictTone(c.verdict)}>{c.verdict}</Badge>
                </div>
                <div className={styles.rationale}>{c.rationale}</div>
                {requestedEvidence.length > 0 && (
                  <div className={styles.section}>Requested: {requestedEvidence.join("; ")}</div>
                )}
                {alternativeExplanations.length > 0 && (
                  <div className={styles.section}>
                    Alternatives considered: {alternativeExplanations.join("; ")}
                  </div>
                )}
              </div>
            );
          })
      )}
    </GlassSurface>
  );
}
