import type { Hypothesis } from "../../api/types";
import { MonoLabel } from "../primitives/MonoLabel";
import { Badge } from "../primitives/Badge";
import { ConfidenceBar } from "../primitives/ConfidenceBar";
import { hypothesisStatusTone } from "../primitives/semantics";
import styles from "./HypothesisSelector.module.css";

interface HypothesisSelectorProps {
  hypotheses: Hypothesis[];
  focusedId: string | null;
  onSelect: (id: string) => void;
}

export function HypothesisSelector({ hypotheses, focusedId, onSelect }: HypothesisSelectorProps) {
  if (hypotheses.length === 0) return null;
  return (
    <div className={styles.row}>
      {hypotheses.map((h) => (
        <button
          key={h.hypothesis_id}
          className={`${styles.item} ${h.hypothesis_id === focusedId ? styles.active : ""}`}
          onClick={() => onSelect(h.hypothesis_id)}
        >
          <MonoLabel>{h.hypothesis_id}</MonoLabel>
          <div className={styles.confidence}>
            <ConfidenceBar value={h.confidence} compact showValue={false} tone={hypothesisStatusTone(h.status)} />
          </div>
          <Badge tone={hypothesisStatusTone(h.status)}>{h.status}</Badge>
        </button>
      ))}
    </div>
  );
}
