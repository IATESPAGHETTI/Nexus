import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { approveRecoveryPlan } from "../../api/client";
import type { IncidentState, NexusEvent } from "../../api/types";
import {
  orderEvents,
  type CommandCenterModel,
  type EvidenceLine,
  type RecoveryStage,
} from "../../lib/presentation";
import { AgentFlow } from "./AgentFlow";
import { AgentConversation } from "./AgentConversation";
import { PlainEnglishBox } from "./PlainEnglishBox";
import styles from "./IncidentHumanCard.module.css";

interface Props {
  model: CommandCenterModel;
  incident: IncidentState;
  events: NexusEvent[] | undefined;
  /** live count of reachable agent services; 0 + no events = nothing is running */
  agentsOnline?: number;
}

const STATUS_HEADLINE: Record<CommandCenterModel["status"], string> = {
  INVESTIGATING: "Investigating",
  DIAGNOSED: "Root cause supported",
  ABSTAINED: "NEXUS abstained",
  RESOLVED: "Recovered",
};

function formatTime(iso: string | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

function toneFor(kind: CommandCenterModel["decision"]["kind"]): string {
  if (kind === "ABSTAINED") return styles.toneAmber;
  if (kind === "DIAGNOSED" || kind === "RESOLVED") return styles.toneGreen;
  return styles.toneRed;
}

// Agent interpretations can run to a paragraph; show a few lines, expand on demand.
function ClampedText({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  const long = text.length > 260;
  return (
    <div>
      <div className={!open && long ? styles.clamped : undefined}>{text}</div>
      {long && (
        <button type="button" className={styles.moreBtn} onClick={() => setOpen((v) => !v)}>
          {open ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
}

/** compact = names only. The full text is shown once, under "What each agent reported". */
function EvidenceList({ lines, empty, compact = false }: { lines: EvidenceLine[]; empty: string; compact?: boolean }) {
  if (!lines.length) return <p className={styles.emptyNote}>{empty}</p>;
  return (
    <ul className={styles.evidenceList}>
      {lines.map((l, i) => (
        <li key={i} className={styles.evidenceItemNeutral}>
          <strong>{l.agent}</strong>
          <span className={styles.lineMeta}>
            {" "}
            · {l.checks} system check{l.checks === 1 ? "" : "s"}
          </span>
          {!compact && <ClampedText text={l.text} />}
        </li>
      ))}
    </ul>
  );
}

const STAGES: { key: RecoveryStage[]; label: string }[] = [
  { key: ["EXECUTING", "EXECUTION_FAILED"], label: "Executing" },
  { key: ["VERIFYING", "VERIFICATION_FAILED"], label: "Verifying" },
  { key: ["RECOVERED"], label: "Recovered" },
];

function stageIndex(stage: RecoveryStage): number {
  return STAGES.findIndex((s) => s.key.includes(stage));
}

function useDecide(incident: IncidentState) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (decision: "APPROVED" | "REJECTED") =>
      approveRecoveryPlan(incident.incident_id, decision, "operator"),
    onSuccess: (state) => queryClient.setQueryData(["incident", incident.incident_id], state),
  });
}

/**
 * Shown at the TOP of the card the moment a real recovery plan is waiting on a
 * person (or its approval window has closed), so it is never buried under the
 * seven question cards. Reads only real recovery/approval state.
 */
function ApprovalBanner({ model, incident }: { model: CommandCenterModel; incident: IncidentState }) {
  const decide = useDecide(incident);
  const rec = model.recovery;
  if (!rec || (rec.stage !== "AWAITING_APPROVAL" && rec.stage !== "EXPIRED")) return null;

  if (rec.stage === "EXPIRED") {
    return (
      <div className={`${styles.approvalBanner} ${styles.approvalExpired}`}>
        <div>
          <div className={styles.approvalTitle}>APPROVAL WINDOW CLOSED. NOTHING WAS EXECUTED</div>
          <p className={styles.approvalText}>
            NEXUS stopped waiting, so nothing ran. The plan is saved: if you approve it now, NEXUS re-checks it against the
            safety rules, runs it, and measures the live service again.
          </p>
          {decide.isError && <span className={styles.errorNote}>Could not record the decision: {String(decide.error)}</span>}
        </div>
        <div className={styles.approvalBtns}>
          <button type="button" className={styles.approveBtn} disabled={decide.isPending} onClick={() => decide.mutate("APPROVED")}>
            APPROVE SAVED PLAN
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.approvalBanner}>
      <div>
        <div className={styles.approvalTitle}>RECOVERY IS WAITING FOR YOUR APPROVAL</div>
        <p className={styles.approvalText}>
          Proposed: <b>{rec.actions.map((a) => a.label).join(", ") || "no allowed action"}</b>
          {rec.approval?.requested_at ? ` · requested ${formatTime(rec.approval.requested_at)}` : ""}. Nothing runs until you decide,
          and NEXUS only waits for a limited time.
        </p>
        {decide.isError && <span className={styles.errorNote}>Could not record the decision: {String(decide.error)}</span>}
      </div>
      <div className={styles.approvalBtns}>
        <button type="button" className={styles.approveBtn} disabled={decide.isPending} onClick={() => decide.mutate("APPROVED")}>
          APPROVE RECOVERY
        </button>
        <button type="button" className={styles.keepBtn} disabled={decide.isPending} onClick={() => decide.mutate("REJECTED")}>
          KEEP INVESTIGATING
        </button>
      </div>
    </div>
  );
}

function RecoveryBlock({ model, incident }: { model: CommandCenterModel; incident: IncidentState }) {
  const decide = useDecide(incident);

  const rec = model.recovery;
  const status = model.status;

  if (!rec) {
    if (status === "ABSTAINED") {
      return (
        <div className={styles.recoveryCard}>
          <div className={styles.notExecuted}>RECOVERY NOT EXECUTED</div>
          <p className={styles.decisionText}>
            NEXUS refused to perform a recovery because the root cause was not sufficiently supported.
          </p>
        </div>
      );
    }
    if (status === "DIAGNOSED") {
      const node = model.pipeline.recovery_agent;
      return (
        <div className={styles.recoveryCard}>
          <div className={styles.recoveryHeader}>
            <span className={styles.recoveryProtocol}>ROOT CAUSE SUPPORTED</span>
            <span className={styles.recoveryStatus}>{node.status === "working" ? "Drafting a plan" : "No plan yet"}</span>
          </div>
          <p className={styles.decisionText}>
            {node.status === "working"
              ? "The Recovery Agent is drafting a bounded recovery plan. Nothing is available to approve yet."
              : "No recovery plan has been recorded for this incident."}
          </p>
        </div>
      );
    }
    return (
      <div className={styles.recoveryCard}>
        <div className={styles.recoveryHeader}>
          <span className={styles.recoveryProtocol}>NOT YET</span>
        </div>
        <p className={styles.decisionText}>
          A recovery is only proposed after a diagnosis is supported by evidence and survives the critic.
        </p>
      </div>
    );
  }

  const idx = stageIndex(rec.stage);
  const failed = rec.stage === "EXECUTION_FAILED" || rec.stage === "VERIFICATION_FAILED";
  const banner: Record<RecoveryStage, string> = {
    AWAITING_APPROVAL: "RECOVERY AVAILABLE",
    REJECTED_BY_SAFETY: "RECOVERY BLOCKED BY SAFETY CHECKS",
    DECLINED: "RECOVERY DECLINED",
    EXPIRED: "APPROVAL WINDOW EXPIRED",
    EXECUTING: "EXECUTING",
    EXECUTION_FAILED: "RECOVERY FAILED",
    VERIFYING: "VERIFYING",
    VERIFICATION_FAILED: "RECOVERY NOT VERIFIED",
    RECOVERED: "RECOVERED",
  };

  return (
    <div className={styles.recoveryCard}>
      <div className={styles.recoveryHeader}>
        <span className={`${styles.recoveryBanner} ${rec.stage === "RECOVERED" ? styles.toneGreen : failed || rec.stage === "REJECTED_BY_SAFETY" ? styles.toneRed : styles.toneIndigo}`}>
          {banner[rec.stage]}
        </span>
        <span className={styles.recoveryStatus}>Risk: {rec.risk}</span>
      </div>

      <div className={styles.recoveryFact}>
        <span className={styles.recoveryFactLabel}>Problem</span>
        <span>{model.belief?.statement ?? incident.description}</span>
      </div>
      <div className={styles.recoveryFact}>
        <span className={styles.recoveryFactLabel}>Proposed action</span>
        <span>
          {rec.actions.length ? (
            rec.actions.map((a, i) => (
              <span key={i} className={styles.actionLine}>
                {a.label}
                {a.rationale ? <span className={styles.lineMeta}> — {a.rationale}</span> : null}
              </span>
            ))
          ) : (
            "No allowed action survived safety validation."
          )}
        </span>
      </div>
      {rec.blastRadius ? (
        <div className={styles.recoveryFact}>
          <span className={styles.recoveryFactLabel}>Blast radius</span>
          <span>{rec.blastRadius}</span>
        </div>
      ) : null}
      {rec.rollbackPlan ? (
        <div className={styles.recoveryFact}>
          <span className={styles.recoveryFactLabel}>If it goes wrong</span>
          <span>{rec.rollbackPlan}</span>
        </div>
      ) : null}

      {rec.stage === "AWAITING_APPROVAL" && (
        <div className={styles.approvalRow}>
          <button
            type="button"
            className={styles.approveBtn}
            disabled={decide.isPending}
            onClick={() => decide.mutate("APPROVED")}
          >
            APPROVE RECOVERY
          </button>
          <button
            type="button"
            className={styles.keepBtn}
            disabled={decide.isPending}
            onClick={() => decide.mutate("REJECTED")}
            title="Declines this plan. Nothing is executed."
          >
            KEEP INVESTIGATING
          </button>
          {decide.isError && <span className={styles.errorNote}>Could not record the decision: {String(decide.error)}</span>}
        </div>
      )}

      {rec.stage === "REJECTED_BY_SAFETY" && (
        <p className={styles.decisionText}>
          {rec.approval?.reason ?? "The plan did not pass validation."} No action was taken.
        </p>
      )}
      {rec.stage === "DECLINED" && <p className={styles.decisionText}>The operator declined this plan. No action was taken.</p>}
      {rec.stage === "EXPIRED" && (
        <p className={styles.decisionText}>
          NEXUS stopped waiting for a decision, so nothing was executed. The plan is saved and can still be approved.
        </p>
      )}

      {idx >= 0 && (
        <ol className={styles.stageStrip}>
          {STAGES.map((s, i) => (
            <li
              key={s.label}
              className={`${styles.stageStep} ${i < idx || rec.stage === "RECOVERED" ? styles.stageDone : ""} ${
                i === idx ? (failed ? styles.stageFailed : rec.stage === "RECOVERED" ? "" : styles.stageCurrent) : ""
              }`}
            >
              {s.label === "Recovered" && rec.stage === "VERIFICATION_FAILED" ? "Not recovered" : s.label}
            </li>
          ))}
        </ol>
      )}
      {rec.verification && (
        <div className={styles.verifyBox}>
          <div className={styles.verifyTitle}>Live check after the fix</div>
          {rec.verification.checks.map((c) => (
            <div key={c.path} className={styles.verifyRow}>
              <code>GET {c.path}</code>
              <span>
                median {c.medianMs} ms (limit {rec.verification!.limitMs} ms) · {c.failures}/{c.requests} failed
              </span>
            </div>
          ))}
        </div>
      )}
      {failed && (
        <p className={styles.decisionText}>
          {rec.stage === "EXECUTION_FAILED"
            ? "At least one action did not complete. The incident stays open."
            : "The action ran, but the follow-up check did not confirm recovery. The incident stays open."}
        </p>
      )}
    </div>
  );
}

function TechnicalDetails({ model, incident, events }: Props) {
  const [open, setOpen] = useState(false);
  const ordered = orderEvents(events);
  const mcp = ordered.filter((e) => e.event_type === "MCP_TOOL_CALL");
  const a2a = ordered.filter((e) => e.event_type === "A2A_MESSAGE_SENT");
  const evidenceIds = Object.values(incident.agent_findings ?? {}).flatMap((f) => f.evidence.map((e) => e.evidence_id));

  return (
    <div className={styles.techDrawerWrapper}>
      <button type="button" className={styles.techDrawerBtn} onClick={() => setOpen((v) => !v)} aria-expanded={open}>
        <div className={styles.techBtnContent}>
          <span className={styles.codeIcon}>&lt;/&gt;</span>
          <span>Technical Details</span>
          <span className={styles.techSubtitle}>(IDs, MCP calls, A2A messages, raw events, JSON)</span>
        </div>
        <span className={`${styles.chevron} ${open ? styles.chevronOpen : ""}`}>▾</span>
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            className={styles.techDrawerContent}
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
          >
            <div className={styles.techGrid}>
              <div className={styles.techRow}>
                <span className={styles.techKey}>Incident ID</span>
                <code className={styles.techCode}>{model.incidentId}</code>
              </div>
              <div className={styles.techRow}>
                <span className={styles.techKey}>Hypotheses</span>
                <div className={styles.techTokenList}>
                  {incident.hypotheses.length ? (
                    incident.hypotheses.map((h) => (
                      <span key={h.hypothesis_id} className={styles.techToken}>
                        {h.hypothesis_id} · {h.status} · {Math.round(h.confidence * 100)}%
                      </span>
                    ))
                  ) : (
                    <span className={styles.techNone}>none recorded</span>
                  )}
                </div>
              </div>
              <div className={styles.techRow}>
                <span className={styles.techKey}>Evidence IDs</span>
                <div className={styles.techTokenList}>
                  {evidenceIds.length ? (
                    evidenceIds.map((id) => (
                      <span key={id} className={styles.techToken}>
                        {id}
                      </span>
                    ))
                  ) : (
                    <span className={styles.techNone}>none recorded</span>
                  )}
                </div>
              </div>
              <div className={styles.techRow}>
                <span className={styles.techKey}>MCP tool calls ({mcp.length})</span>
                <div className={styles.techTokenList}>
                  {mcp.length ? (
                    mcp.map((e) => (
                      <span key={e.event_id} className={styles.techMcpToken}>
                        {e.source} → {String(e.payload?.tool)} {JSON.stringify(e.payload?.arguments ?? {})}
                      </span>
                    ))
                  ) : (
                    <span className={styles.techNone}>none recorded</span>
                  )}
                </div>
              </div>
              <div className={styles.techRow}>
                <span className={styles.techKey}>A2A messages ({a2a.length})</span>
                <div className={styles.techTokenList}>
                  {a2a.length ? (
                    a2a.map((e) => (
                      <span key={e.event_id} className={styles.techToken}>
                        {e.source} → {e.target} · task {String(e.payload?.task_id ?? "?")} · ctx {String(e.payload?.context_id ?? "?")}
                      </span>
                    ))
                  ) : (
                    <span className={styles.techNone}>none recorded</span>
                  )}
                </div>
              </div>
              <div className={styles.rawJsonBox}>
                <div className={styles.rawJsonTitle}>RAW EVENTS ({ordered.length})</div>
                <pre className={styles.rawJsonPre}>{JSON.stringify(ordered, null, 2)}</pre>
              </div>
              <div className={styles.rawJsonBox}>
                <div className={styles.rawJsonTitle}>RAW INCIDENT STATE</div>
                <pre className={styles.rawJsonPre}>{JSON.stringify(incident, null, 2)}</pre>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export function IncidentHumanCard({ model, incident, events, agentsOnline }: Props) {
  const { decision, belief, challenge } = model;
  const stalled = model.status === "INVESTIGATING" && !model.latest && agentsOnline === 0;
  const terminal = model.status === "ABSTAINED" || model.status === "RESOLVED";

  return (
    <div className={styles.cardContainer}>
      <ApprovalBanner model={model} incident={incident} />

      {/* 1 — What happened? */}
      <section className={styles.sectionHeader}>
        <div className={styles.questionTag}>
          <span className={styles.questionNumber}>01</span>
          <span>WHAT HAPPENED?</span>
        </div>
        <div className={styles.incidentTitleRow}>
          <h2 className={styles.incidentTitle}>{model.description}</h2>
          <span className={`${styles.statusBadge} ${toneFor(decision.kind)}`}>{STATUS_HEADLINE[model.status]}</span>
        </div>
        <div className={styles.failureGrid}>
          <div className={styles.failureItem}>
            <span className={styles.failureLabel}>Reported</span>
            <span className={styles.failureVal}>{formatTime(model.createdAt)}</span>
          </div>
          <div className={styles.failureItem}>
            <span className={styles.failureLabel}>Last update</span>
            <span className={styles.failureVal}>{formatTime(model.updatedAt)}</span>
          </div>
          <div className={styles.failureItem}>
            <span className={styles.failureLabel}>Confused by a word?</span>
            <a className={styles.failureVal} href="#plain-english">Jump to plain English ↓</a>
          </div>
        </div>
      </section>

      {/* 2 — What is NEXUS doing? */}
      <section className={styles.section}>
        <div className={styles.questionTag}>
          <span className={styles.questionNumber}>02</span>
          <span>WHAT IS NEXUS DOING?</span>
        </div>
        <div className={styles.investigatingBox}>
          <div className={styles.activityIndicator}>
            {model.status === "INVESTIGATING" && !stalled && <span className={styles.activityPulse} />}
            <span className={styles.activityHeading}>
              {stalled
                ? "Nothing is investigating yet"
                : model.status === "INVESTIGATING"
                ? "NEXUS is investigating"
                : model.status === "DIAGNOSED"
                ? "NEXUS supported a root cause"
                : model.status === "RESOLVED"
                ? "NEXUS recovered the system"
                : "NEXUS stopped without a diagnosis"}
            </span>
          </div>
          <p className={styles.activityText}>
            {stalled
              ? "The incident is recorded, but no agent services are reachable, so no investigation has started. Start them per docs/DEMO_RUNBOOK.md."
              : model.latest
              ? `Latest: ${model.latest.label} — ${model.latest.actor}${model.latest.detail ? ` (${model.latest.detail})` : ""}.`
              : "No events recorded yet."}
          </p>
          <AgentFlow model={model} events={events} animated={!stalled && !terminal} />
          <AgentConversation events={events} model={model} animated={!stalled && !terminal} />
        </div>
      </section>

      {/* 3 — What evidence did it find? */}
      <section className={styles.section}>
        <div className={styles.questionTag}>
          <span className={styles.questionNumber}>03</span>
          <span>WHAT EVIDENCE DID IT FIND?</span>
        </div>
        <div className={styles.evidenceCol}>
          <div className={styles.evidenceColTitle}>
            <span className={styles.evidenceIconSupporting}>✓</span>
            <span>What each agent reported</span>
          </div>
          <EvidenceList
            lines={model.findings}
            empty={terminal ? "No agent reported evidence." : "No agent has reported evidence yet."}
          />
          {model.silentAgents.length > 0 && (
            <p className={styles.errorNote}>No response from: {model.silentAgents.join(", ")}.</p>
          )}
          {model.findings.length === 0 && model.silentAgents.length > 0 && (
            <p className={styles.errorNote}>
              No diagnostic agent returned evidence. The usual causes are the agents' model provider rejecting their
              requests (an invalid or expired API key, or an exhausted quota) or an agent service being down. Check the
              agent service logs; the exact events are under Technical Details.
            </p>
          )}
        </div>
        {belief && (
          <div className={styles.evidenceColumns}>
            <div className={styles.evidenceCol}>
              <div className={styles.evidenceColTitle}>
                <span className={styles.evidenceIconSupporting}>✓</span>
                <span>Points toward the possible cause</span>
              </div>
              <EvidenceList compact lines={belief.supporting} empty="No evidence was linked in favour." />
            </div>
            <div className={styles.evidenceCol}>
              <div className={styles.evidenceColTitle}>
                <span className={styles.evidenceIconContradicting}>✕</span>
                <span>Points against it</span>
              </div>
              <EvidenceList compact lines={belief.contradicting} empty="No evidence was linked against it." />
            </div>
            <div className={styles.evidenceCol}>
              <div className={styles.evidenceColTitle}>
                <span className={styles.evidenceIconPending}>⏳</span>
                <span>Still missing</span>
              </div>
              {belief.missing.length ? (
                <ul className={styles.evidenceList}>
                  {belief.missing.map((m, i) => (
                    <li key={i} className={styles.evidenceItemPending}>
                      {m}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className={styles.emptyNote}>Nothing recorded as missing.</p>
              )}
            </div>
          </div>
        )}
      </section>

      {/* 4 + 5 */}
      <div className={styles.twoColumnGrid}>
        <section className={styles.section}>
          <div className={styles.questionTag}>
            <span className={styles.questionNumber}>04</span>
            <span>WHAT DOES IT CURRENTLY BELIEVE?</span>
          </div>
          <div className={styles.beliefBox}>
            <div className={styles.beliefKicker}>Possible cause</div>
            {belief ? (
              <>
                <div className={styles.beliefTitle}>{belief.statement}</div>
                <p className={styles.beliefDesc}>
                  Confidence reported by the Evidence Agent: {belief.confidencePct}% · Status: {belief.statusLabel}
                </p>
              </>
            ) : (
              <p className={styles.beliefDesc}>
                {terminal ? "NEXUS did not propose a possible cause." : "No possible cause has been proposed yet."}
              </p>
            )}
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.questionTag}>
            <span className={styles.questionNumber}>05</span>
            <span>DID IT CHALLENGE ITSELF?</span>
          </div>
          <div className={styles.challengeBox}>
            <div className={styles.beliefKicker}>Self-challenge</div>
            {challenge ? (
              <>
                <div className={styles.challengeTitle}>
                  {challenge.verdictLabel}
                  <span className={styles.lineMeta}>
                    {" "}
                    · reviewed {challenge.reviews} time{challenge.reviews === 1 ? "" : "s"}
                  </span>
                </div>
                {challenge.rationale && (
                  <blockquote className={styles.challengeQuote}>
                    <ClampedText text={challenge.rationale} />
                  </blockquote>
                )}
                {challenge.alternatives.length > 0 && (
                  <div className={styles.miniList}>
                    <strong>Other explanations it checked</strong>
                    <ul>{challenge.alternatives.map((a, i) => <li key={i}>{a}</li>)}</ul>
                  </div>
                )}
                {challenge.assumptions.length > 0 && (
                  <div className={styles.miniList}>
                    <strong>Assumptions it could not verify</strong>
                    <ul>{challenge.assumptions.map((a, i) => <li key={i}>{a}</li>)}</ul>
                  </div>
                )}
                {challenge.requested.length > 0 && (
                  <div className={styles.miniList}>
                    <strong>Evidence it asked for</strong>
                    <ul>{challenge.requested.map((a, i) => <li key={i}>{a}</li>)}</ul>
                  </div>
                )}
              </>
            ) : (
              <p className={styles.beliefDesc}>
                {terminal
                  ? "The Root-Cause Critic never reviewed a possible cause in this run."
                  : "Not yet — the Root-Cause Critic reviews a possible cause once one exists."}
              </p>
            )}
          </div>
        </section>
      </div>

      {/* 6 + 7 */}
      <div className={styles.twoColumnGrid}>
        <section className={styles.section}>
          <div className={styles.questionTag}>
            <span className={styles.questionNumber}>06</span>
            <span>WHAT DID IT DECIDE?</span>
          </div>
          <div className={styles.decisionCard}>
            <div className={styles.decisionBanner}>
              <span className={`${styles.decisionPill} ${toneFor(decision.kind)}`}>
                {decision.kind === "INVESTIGATING"
                  ? "NOT DECIDED YET"
                  : decision.kind === "DIAGNOSED"
                  ? "ROOT CAUSE SUPPORTED"
                  : decision.kind === "RESOLVED"
                  ? "RESOLVED"
                  : "NEXUS ABSTAINED"}
              </span>
              {decision.loopsUsed != null && decision.maxLoops != null && (
                <span className={styles.decisionSub}>
                  Reviewed {decision.loopsUsed} of at most {decision.maxLoops} rounds
                </span>
              )}
            </div>
            {decision.kind === "ABSTAINED" && (
              <p className={styles.decisionText}>
                {belief
                  ? "We found a possible explanation, but we could not prove it."
                  : "NEXUS could not form a supported explanation."}
              </p>
            )}
            {decision.kind === "INVESTIGATING" && (
              <p className={styles.decisionText}>The investigation is still running. No decision has been made.</p>
            )}
            {decision.reason && <p className={styles.decisionText}>Why it stopped: {decision.reason}</p>}
            {decision.reasons.map((r) => (
              <div key={r.label} className={styles.reasonBlock}>
                <div className={styles.reasonLabel}>{r.label}</div>
                {r.items.length > 0 && <ul>{r.items.map((it, i) => <li key={i}>{it}</li>)}</ul>}
              </div>
            ))}
          </div>
        </section>

        <section className={styles.section}>
          <div className={styles.questionTag}>
            <span className={styles.questionNumber}>07</span>
            <span>CAN IT RECOVER?</span>
          </div>
          <RecoveryBlock model={model} incident={incident} />
        </section>
      </div>

      <PlainEnglishBox model={model} incident={incident} events={events} />

      <TechnicalDetails model={model} incident={incident} events={events} />
    </div>
  );
}
