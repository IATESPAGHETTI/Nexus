import type { PropsWithChildren } from "react";

/** Reserved for IDs, tool names, and event types — the one deliberate
 * "technical precision" typographic cue, used sparingly. */
export function MonoLabel({ children }: PropsWithChildren) {
  return <span className="nx-mono">{children}</span>;
}
