import type { CommandCenterModel, AgentKey, NodeStatus } from "../../lib/presentation";
import styles from "./StageTracker.module.css";

type StageState = "waiting" | "working" | "done" | "failed" | "skipped";

interface Row {
  name: string;
  state: StageState;
  text: string;
}

interface Stage {
  title: string;
  /** fixed, data-free description of what this stage is for */
  purpose: string;
  state: StageState;
  /** what really happened (from the incident), or null */
  result: string | null;
  rows?: Row[];
}

const SPECIALISTS: { key: AgentKey; name: string; role: string }[] = [
  { key: "metrics_agent", name: "Metrics Agent", role: "request speed and errors" },
  { key: "logs_traces_agent", name: "Logs & Traces Agent", role: "what happened, and when" },
  { key: "change_analysis_agent", name: "Change Analysis Agent", role: "recent deployments and config" },
  { key: "database_agent", name: "Database Agent", role: "database health" },
];

const NODE_TO_STATE: Record<NodeStatus, StageState> = {
  idle: "waiting",
  working: "working",
  reported: "done",
  failed: "failed",
};

const STATE_WORD: Record<StageState, string> = {
  waiting: "Waiting",
  working: "Working now",
  done: "Done",
  failed: "Problem",
  skipped: "Not needed",
};

const FIX_PURPOSE = "The Recovery Agent suggests a bounded action. It can only suggest; it cannot run anything.";
const APPROVE_PURPOSE = "Safety rules check the plan, a human approves it, it runs, then NEXUS re-measures the service.";

const short = (text: string, n = 140) => (text.length > n ? `${text.slice(0, n - 1).trimEnd()}…` : text);

function gatherState(states: StageState[]): StageState {
  if (states.every((s) => s === "waiting")) return "waiting";
  if (states.some((s) => s === "working" || s === "waiting")) return "working";
  return states.every((s) => s === "failed") ? "failed" : "done";
}

function recoveryStages(model: CommandCenterModel): { fix: Stage; approve: Stage } {
  const rec = model.recovery;
  const abstained = model.decision.kind === "ABSTAINED";
  const idle: StageState = abstained ? "skipped" : "waiting";
  const agentStatus = model.pipeline.recovery_agent.status;
  const fix: Stage = {
    title: "Propose a fix",
    purpose: FIX_PURPOSE,
    state: agentStatus === "idle" ? idle : NODE_TO_STATE[agentStatus],
    result: rec?.actions.length ? `Proposed: ${rec.actions.map((a) => a.label).join(", ")} (risk ${rec.risk})` : null,
  };

  let state: StageState = idle;
  let result: string | null = abstained ? "No diagnosis, so no recovery was attempted." : null;
  if (rec) {
    switch (rec.stage) {
      case "AWAITING_APPROVAL":
        state = "working";
        result = "Safety checks passed. Waiting for a human to approve or reject.";
        break;
      case "EXECUTING":
        state = "working";
        result = "Approved. Running the action.";
        break;
      case "VERIFYING":
        state = "working";
        result = "Action ran. Measuring the live service.";
        break;
      case "RECOVERED":
        state = "done";
        result = "Verified: the live check passed.";
        break;
      case "VERIFICATION_FAILED":
        state = "failed";
        result = "The action ran but the live check did not confirm recovery. Incident stays open.";
        break;
      case "EXECUTION_FAILED":
        state = "failed";
        result = "The action failed to run.";
        break;
      case "REJECTED_BY_SAFETY":
        state = "failed";
        result = "Blocked by the safety checks. Nothing was executed.";
        break;
      case "DECLINED":
        state = "failed";
        result = "A human declined the plan. Nothing was executed.";
        break;
      case "EXPIRED":
        state = "failed";
        result = "Nobody approved in time. Nothing was executed.";
        break;
    }
  }
  return { fix, approve: { title: "Approve, run and verify", purpose: APPROVE_PURPOSE, state, result } };
}

function buildStages(model: CommandCenterModel | null | undefined): Stage[] {
  const specialistRows: Row[] = SPECIALISTS.map((s) => {
    const node = model?.pipeline[s.key];
    const state = node ? NODE_TO_STATE[node.status] : "waiting";
    const text = node && node.status !== "idle" ? node.note ?? STATE_WORD[state] : s.role;
    return { name: s.name, state, text };
  });
  const belief = model?.belief;
  const challenge = model?.challenge;
  const decision = model?.decision;
  const decided = decision !== undefined && decision.kind !== "INVESTIGATING";

  const tail: Stage[] = model
    ? (() => {
        const r = recoveryStages(model);
        return [r.fix, r.approve];
      })()
    : [
        { title: "Propose a fix", purpose: FIX_PURPOSE, state: "waiting", result: null },
        { title: "Approve, run and verify", purpose: APPROVE_PURPOSE, state: "waiting", result: null },
      ];

  return [
    {
      title: "Gather evidence",
      purpose: "Four specialist agents each read one kind of data through their tools, in parallel.",
      state: gatherState(specialistRows.map((r) => r.state)),
      result: null,
      rows: specialistRows,
    },
    {
      title: "Form possible causes",
      purpose: "The Evidence Agent combines the findings into ranked possible causes.",
      state: model ? NODE_TO_STATE[model.pipeline.evidence_agent.status] : "waiting",
      result: belief ? `Top cause (${belief.confidencePct}%): ${short(belief.statement)}` : null,
    },
    {
      title: "Challenge the top cause",
      purpose: "The Root-Cause Critic tries to prove it wrong and asks for missing evidence.",
      state: model ? NODE_TO_STATE[model.pipeline.root_cause_critic.status] : "waiting",
      result: challenge ? `${challenge.verdictLabel} (reviewed ${challenge.reviews} time${challenge.reviews === 1 ? "" : "s"})` : null,
    },
    {
      title: "Decide",
      purpose: "A supported diagnosis, or an honest “not enough evidence”. Never forced; at most 3 rounds.",
      state: decided ? "done" : "waiting",
      result: decided
        ? decision.kind === "ABSTAINED"
          ? `Stopped without a diagnosis${decision.reason ? `: ${short(decision.reason, 110)}` : ""}`
          : "Root cause supported by the Critic."
        : null,
    },
    ...tail,
  ];
}

/**
 * Six fixed stages, always visible, top to bottom. Nothing opens or fades in:
 * only each stage's state changes. With `live` off it shows the structure with
 * no states or results; with it on, every state and result line comes from the
 * real incident (`buildCommandCenterModel`), never invented.
 */
export function StageTracker({ live, model }: { live: boolean; model: CommandCenterModel | null | undefined }) {
  const showState = live && model !== undefined;
  const stages = buildStages(showState ? model : undefined);
  return (
    <ol className={styles.tracker} aria-label="Investigation stages">
      {stages.map((stage, i) => {
        const state: StageState = showState ? stage.state : "waiting";
        return (
          <li key={stage.title} className={`${styles.stage} ${styles[state]}`}>
            <div className={styles.rail}>
              <span className={styles.badge}>{state === "done" ? "✓" : state === "failed" ? "!" : i + 1}</span>
              {i < stages.length - 1 && <span className={styles.line} />}
            </div>
            <div className={styles.body}>
              <div className={styles.head}>
                <span className={styles.stageTitle}>{stage.title}</span>
                {showState && <span className={styles.stateWord}>{STATE_WORD[state]}</span>}
              </div>
              <div className={styles.purpose}>{stage.purpose}</div>
              {showState && stage.result && <div className={styles.result}>{stage.result}</div>}
              {stage.rows && (
                <ul className={styles.rows}>
                  {stage.rows.map((r) => (
                    <li key={r.name} className={`${styles.row} ${showState ? styles[`row_${r.state}`] : ""}`}>
                      <span className={styles.rowDot} />
                      <span className={styles.rowName}>{r.name}</span>
                      <span className={styles.rowText}>{r.text}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
