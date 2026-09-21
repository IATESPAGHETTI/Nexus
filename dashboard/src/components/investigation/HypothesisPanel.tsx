import { useEffect, useState } from "react";
import { GlassSurface } from "../primitives/GlassSurface";
import { HypothesisSelector } from "./HypothesisSelector";
import { HypothesisConstellation } from "./HypothesisConstellation";
import { RevisionBanner } from "./RevisionBanner";
import type { Critique, Hypothesis } from "../../api/types";
import type { EvidenceLookupEntry } from "../../lib/derive";
import styles from "./HypothesisPanel.module.css";

interface HypothesisPanelProps {
  hypotheses: Hypothesis[];
  critiques: Critique[];
  evidenceLookup: Record<string, EvidenceLookupEntry>;
}

export function HypothesisPanel({ hypotheses, critiques, evidenceLookup }: HypothesisPanelProps) {
  const [focusedId, setFocusedId] = useState<string | null>(null);

  useEffect(() => {
    if (hypotheses.length === 0) {
      setFocusedId(null);
      return;
    }
    if (!focusedId || !hypotheses.some((h) => h.hypothesis_id === focusedId)) {
      // Default to the leading (highest-confidence) hypothesis.
      setFocusedId(hypotheses[0].hypothesis_id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hypotheses]);

  const focused = hypotheses.find((h) => h.hypothesis_id === focusedId);
  const latestCritique = focused
    ? critiques.filter((c) => c.hypothesis_id === focused.hypothesis_id).slice(-1)[0]
    : undefined;

  return (
    <GlassSurface className={styles.wrap}>
      <div className={styles.title}>Hypotheses</div>
      {hypotheses.length === 0 ? (
        <div className={styles.empty}>No hypotheses proposed yet.</div>
      ) : (
        <>
          <HypothesisSelector hypotheses={hypotheses} focusedId={focusedId} onSelect={setFocusedId} />
          {focused && (
            <>
              <HypothesisConstellation hypothesis={focused} evidenceLookup={evidenceLookup} />
              <RevisionBanner hypothesis={focused} critique={latestCritique} />
            </>
          )}
        </>
      )}
    </GlassSurface>
  );
}
