import type { NexusEvent } from "../../api/types";

/** Quiet loop counter — "Cycle N of M" — derived from real
 * RE_EVALUATION_STARTED events (payload {loop, max_loops}), never a
 * fabricated progress animation. */
export function ReEvaluationLoopIndicator({ events }: { events: NexusEvent[] }) {
  const starts = events.filter((e) => e.event_type === "RE_EVALUATION_STARTED");
  if (starts.length === 0) return null;
  const last = starts[starts.length - 1];
  const loop = last.payload?.loop;
  const maxLoops = last.payload?.max_loops;
  if (typeof loop !== "number" || typeof maxLoops !== "number") return null;

  return (
    <div style={{ fontSize: 12, color: "var(--nx-ink-4)", textAlign: "center" }}>
      Cycle {loop} of {maxLoops}
    </div>
  );
}
