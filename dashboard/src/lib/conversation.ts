// Turns the REAL event log into a readable "who asked whom, what came back"
// conversation. Nothing is invented: every row is one recorded event (or the
// events that followed an A2A message from the agent that received it), and the
// wording only translates fixed event names into plain English.

import type { NexusEvent } from "../api/types";
import {
  ACTION_LABELS,
  PIPELINE_AGENTS,
  VERDICT_LABELS,
  actorName,
  orderEvents,
  toolLabel,
} from "./presentation";

export type RowKind = "exchange" | "callback" | "round" | "human" | "guardrail" | "triage";

export interface ConversationRow {
  id: string;
  time: string;
  kind: RowKind;
  from: string;
  to: string;
  /** what was asked / said (plain English) */
  said: string;
  /** the answer that came back, if one is recorded */
  reply: string | null;
  replyFailed?: boolean;
  /** A2A task id, shown small so the exchange can be traced in Technical Details */
  taskId?: string;
}

const ROLE: Record<string, string> = Object.fromEntries(PIPELINE_AGENTS.map((a) => [a.key, a.role]));

function clip(text: string, n = 170): string {
  const t = text.replace(/\s+/g, " ").trim();
  return t.length > n ? `${t.slice(0, n - 1)}…` : t;
}

function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}

function requestText(target: string, hypothesisId: string | null): string {
  switch (target) {
    case "evidence_agent":
      return "Here is what the four investigators found. What could be causing this? Propose possible causes.";
    case "root_cause_critic":
      return `Try to prove ${hypothesisId ?? "the leading explanation"} wrong. Look for evidence that contradicts it.`;
    case "recovery_agent":
      return "A cause is supported. Propose a safe, limited fix.";
    default:
      return `Investigate your area (${ROLE[target] ?? "your specialty"}) and report back with evidence.`;
  }
}

function replyFor(target: string, window: NexusEvent[]): { text: string | null; failed: boolean } {
  const mine = window.filter((e) => e.source === target);
  if (target === "evidence_agent") {
    const made = mine.filter((e) => e.event_type === "HYPOTHESIS_CREATED");
    if (!made.length) return { text: null, failed: false };
    const first = String(made[0].payload?.statement ?? "");
    return {
      text: `Proposed ${plural(made.length, "possible cause")}. Top one: “${clip(first, 150)}”`,
      failed: false,
    };
  }
  if (target === "root_cause_critic") {
    const c = mine.find((e) => e.event_type === "CRITIC_CHALLENGE");
    if (!c) return { text: null, failed: false };
    const verdict = String(c.payload?.verdict ?? "");
    const label = (VERDICT_LABELS as Record<string, string>)[verdict] ?? verdict;
    const why = c.payload?.rationale ? ` — ${clip(String(c.payload.rationale), 190)}` : "";
    return { text: `Verdict: ${label}${why}`, failed: false };
  }
  if (target === "recovery_agent") {
    const p = mine.find((e) => e.event_type === "RECOVERY_PROPOSED");
    if (!p) return { text: null, failed: false };
    const acts = ((p.payload?.actions as { action?: string }[] | undefined) ?? [])
      .map((a) => ACTION_LABELS[a.action ?? ""] ?? a.action ?? "")
      .filter(Boolean);
    return { text: `Proposed fix: ${acts.join(", ") || "no allowed action"}`, failed: false };
  }
  // diagnostic agents
  const done = mine.find((e) => e.event_type === "AGENT_COMPLETED");
  const tools = mine.filter((e) => e.event_type === "MCP_TOOL_CALL");
  if (!done && !tools.length) return { text: null, failed: false };
  if (done && done.status === "failed") return { text: "No usable reply came back.", failed: true };
  const kinds = [...new Set(tools.map((e) => toolLabel(String(e.payload?.tool ?? "check"))))];
  const evCount = mine
    .filter((e) => e.event_type === "EVIDENCE_FOUND")
    .reduce((n, e) => n + ((e.payload?.evidence_ids as unknown[] | undefined)?.length ?? 0), 0);
  const conf = typeof done?.payload?.confidence === "number" ? ` · confidence ${Math.round(done.payload.confidence * 100)}%` : "";
  return {
    text: `Ran ${plural(tools.length, "system check")}${kinds.length ? ` (${kinds.join(", ")})` : ""} · returned ${plural(evCount, "piece")} of evidence${conf}`,
    failed: false,
  };
}

export function buildConversation(events: NexusEvent[] | undefined): ConversationRow[] {
  const ordered = orderEvents(events);
  const rows: ConversationRow[] = [];
  let hypothesisInReview: string | null = null;

  ordered.forEach((e, i) => {
    switch (e.event_type) {
      case "INCIDENT_CREATED":
        rows.push({
          id: e.event_id, time: e.timestamp, kind: "callback", from: "Customers", to: "Incident Manager",
          said: clip(String(e.payload?.description ?? "An incident was reported."), 200), reply: "Incident opened. Starting the investigation.",
        });
        break;
      case "AGENTS_SELECTED": {
        const sel = (e.payload?.selected as string[] | undefined) ?? [];
        const skipped = (e.payload?.skipped as { agent: string; reason: string }[] | undefined) ?? [];
        const round = Number(e.payload?.round ?? 1);
        rows.push({
          id: e.event_id, time: e.timestamp, kind: "triage", from: "Incident Manager", to: "Specialists",
          said: `${round > 1 ? `Round ${round}, asking again` : "Choosing who to call"}: ${sel.map(actorName).join(", ") || "nobody"}.${
            skipped.length ? ` Not calling ${skipped.map((s) => actorName(s.agent)).join(", ")} (${skipped[0].reason}).` : ""
          }`,
          reply: null,
        });
        break;
      }
      case "RE_EVALUATION_STARTED":
        hypothesisInReview = e.target ?? null;
        rows.push({
          id: e.event_id, time: e.timestamp, kind: "round", from: "Incident Manager", to: "Root-Cause Critic",
          said: `Review round ${String(e.payload?.loop ?? "?")} of at most ${String(e.payload?.max_loops ?? "?")}: second opinion on ${e.target ?? "the leading explanation"}`,
          reply: null,
        });
        break;
      case "A2A_MESSAGE_SENT": {
        const target = e.target ?? "";
        let j = i + 1;
        while (j < ordered.length && ordered[j].event_type !== "A2A_MESSAGE_SENT") j += 1;
        const reply = replyFor(target, ordered.slice(i + 1, j));
        rows.push({
          id: e.event_id, time: e.timestamp, kind: "exchange", from: actorName(e.source), to: actorName(target),
          said: requestText(target, hypothesisInReview), reply: reply.text, replyFailed: reply.failed,
          taskId: e.payload?.task_id ? String(e.payload.task_id) : undefined,
        });
        break;
      }
      case "EVIDENCE_REQUESTED": {
        const n = (e.payload?.requested_evidence as unknown[] | undefined)?.length ?? 0;
        rows.push({
          id: e.event_id, time: e.timestamp, kind: "callback", from: actorName(e.source), to: actorName(e.target),
          said: `Not convinced yet. Asked for ${plural(n, "more piece")} of evidence, so the investigators will look again.`, reply: null,
        });
        break;
      }
      case "SAFETY_VALIDATION":
        rows.push({
          id: e.event_id, time: e.timestamp, kind: "guardrail", from: "Safety guardrails", to: "Recovery plan",
          said: String(e.payload?.verdict) === "APPROVED_FOR_HUMAN_REVIEW"
            ? "Checked the plan against the allow-list and safety rules: passed, so it may go to a person."
            : `Checked the plan against the safety rules: ${String(e.payload?.verdict ?? "see details")}.`,
          reply: null,
        });
        break;
      case "HUMAN_APPROVAL_REQUESTED":
        rows.push({
          id: e.event_id, time: e.timestamp, kind: "human", from: "Safety guardrails", to: "Human operator",
          said: "Nothing runs until a person approves this plan.", reply: null,
        });
        break;
      case "HUMAN_APPROVAL_GRANTED":
      case "HUMAN_APPROVAL_REJECTED":
        if (e.payload?.approved_by || e.status) {
          rows.push({
            id: e.event_id, time: e.timestamp, kind: "human", from: "Human operator", to: "NEXUS",
            said: e.event_type === "HUMAN_APPROVAL_GRANTED" ? "Approved the plan." : "Declined the plan. Nothing was executed.", reply: null,
          });
        }
        break;
      case "RECOVERY_EXECUTED": {
        const hist = (e.payload?.action_history as { action?: string; status?: string }[] | undefined) ?? [];
        rows.push({
          id: e.event_id, time: e.timestamp, kind: "guardrail", from: "Safety guardrails", to: "Simulated shop",
          said: `Ran the approved action${hist.length === 1 ? "" : "s"}: ${hist.map((h) => ACTION_LABELS[h.action ?? ""] ?? h.action).join(", ") || "none"}`,
          reply: e.payload?.all_succeeded === false ? "At least one action failed." : "Action completed.",
          replyFailed: e.payload?.all_succeeded === false,
        });
        break;
      }
      case "RECOVERY_VERIFIED": {
        const probe = e.payload?.probe as { latency_limit_ms?: number; per_path?: Record<string, { median_ms: number }> } | undefined;
        const parts = Object.entries(probe?.per_path ?? {}).map(([p, v]) => `${p} ${v.median_ms} ms`);
        const ok = e.payload?.verified === true;
        rows.push({
          id: e.event_id, time: e.timestamp, kind: "guardrail", from: "Safety guardrails", to: "Simulated shop",
          said: `Sent real test requests to check the fix${probe?.latency_limit_ms ? ` (must answer under ${probe.latency_limit_ms} ms)` : ""}.`,
          reply: `${ok ? "Passed" : "Not confirmed"}: ${parts.join(" · ") || "no timings recorded"}`,
          replyFailed: !ok,
        });
        break;
      }
      case "INCIDENT_RESOLVED":
        rows.push({
          id: e.event_id, time: e.timestamp, kind: "callback", from: "Incident Manager", to: "Everyone",
          said: "Incident resolved. The shop is back to normal.", reply: null,
        });
        break;
      case "ABSTENTION":
        rows.push({
          id: e.event_id, time: e.timestamp, kind: "callback", from: actorName(e.source), to: "Incident Manager",
          said: "Declined to name a cause: the evidence was not strong enough to be sure.", reply: null,
        });
        break;
      default:
        break;
    }
  });
  return rows;
}

/**
 * Agents the Incident Manager decided NOT to call (and never called later),
 * with the recorded reason. Empty until a real AGENTS_SELECTED event exists.
 */
export function skippedAgents(events: NexusEvent[] | undefined): Record<string, string> {
  const ordered = orderEvents(events);
  const started = new Set(ordered.filter((e) => e.event_type === "AGENT_STARTED").map((e) => e.target ?? ""));
  const out: Record<string, string> = {};
  for (const e of ordered) {
    if (e.event_type !== "AGENTS_SELECTED") continue;
    for (const s of (e.payload?.skipped as { agent: string; reason: string }[] | undefined) ?? []) {
      if (!started.has(s.agent) && !(s.agent in out)) out[s.agent] = s.reason;
    }
  }
  return out;
}
