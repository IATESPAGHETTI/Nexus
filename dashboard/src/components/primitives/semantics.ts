// Single source of truth mapping real backend enums to the 4 semantic tones
// (neutral/green/amber/red). Color must communicate state only — this is the
// one place that decision gets made, so it can't drift between components.
export type SemanticTone = "neutral" | "green" | "amber" | "red";

export function agentStatusTone(status: string): SemanticTone {
  switch (status) {
    case "RUNNING":
    case "WAITING":
      return "amber";
    case "COMPLETED":
      return "green";
    case "FAILED":
      return "red";
    default:
      return "neutral";
  }
}

export function hypothesisStatusTone(status: string): SemanticTone {
  switch (status) {
    case "SUPPORTED":
      return "green";
    case "REJECTED":
    case "ABSTAINED":
      return "red";
    case "CHALLENGED":
    case "NEEDS_EVIDENCE":
    case "UNDER_REVIEW":
      return "amber";
    default:
      return "neutral";
  }
}

export function verdictTone(verdict: string): SemanticTone {
  switch (verdict) {
    case "SUPPORTED":
      return "green";
    case "CONTRADICTED":
    case "ABSTAIN":
      return "red";
    case "INSUFFICIENT_EVIDENCE":
    case "REQUEST_MORE_EVIDENCE":
      return "amber";
    default:
      return "neutral";
  }
}

export function incidentStatusTone(status: string): SemanticTone {
  switch (status) {
    case "RESOLVED":
    case "DIAGNOSED":
      return "green";
    case "ABSTAINED":
      return "amber";
    case "INVESTIGATING":
      return "neutral";
    default:
      return "neutral";
  }
}

export function approvalDecisionTone(decision: string): SemanticTone {
  switch (decision) {
    case "APPROVED":
      return "green";
    case "REJECTED":
    case "EXPIRED":
      return "red";
    case "PENDING":
      return "amber";
    default:
      return "neutral";
  }
}

export function actionStatusTone(status: string): SemanticTone {
  switch (status) {
    case "EXECUTED":
      return "green";
    case "FAILED":
      return "red";
    case "SKIPPED_KILL_SWITCH":
      return "amber";
    default:
      return "neutral";
  }
}
