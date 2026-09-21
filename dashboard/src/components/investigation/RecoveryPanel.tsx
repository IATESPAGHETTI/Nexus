import { useState } from "react";
import { motion } from "motion/react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { GlassSurface } from "../primitives/GlassSurface";
import { StatusDot } from "../primitives/StatusDot";
import { Badge } from "../primitives/Badge";
import { MonoLabel } from "../primitives/MonoLabel";
import { Timestamp } from "../primitives/Timestamp";
import { actionStatusTone, approvalDecisionTone } from "../primitives/semantics";
import { approveRecoveryPlan } from "../../api/client";
import type { IncidentState, NexusEvent, NexusEventType } from "../../api/types";
import styles from "./RecoveryPanel.module.css";

interface RecoveryPanelProps {
  incident: IncidentState;
  events: NexusEvent[];
}

const RECOVERY_STEP_TYPES: { type: NexusEventType; label: string }[] = [
  { type: "RECOVERY_PROPOSED", label: "Plan proposed" },
  { type: "SAFETY_VALIDATION", label: "Safety validated" },
  { type: "HUMAN_APPROVAL_REQUESTED", label: "Approval requested" },
  { type: "HUMAN_APPROVAL_GRANTED", label: "Approved" },
  { type: "HUMAN_APPROVAL_REJECTED", label: "Rejected by human" },
  { type: "RECOVERY_EXECUTED", label: "Executed" },
  { type: "RECOVERY_VERIFIED", label: "Verified" },
  { type: "INCIDENT_RESOLVED", label: "Resolved" },
];

/**
 * Real Phase 8 recovery state — no longer a static "Pending — Phase 8"
 * stub. Renders genuinely from incident.recovery_plan / approval_state /
 * action_history (docs/API_CONTRACT.md "Recovery flow") plus whichever real
 * recovery-related events (RECOVERY_PROPOSED, SAFETY_VALIDATION,
 * HUMAN_APPROVAL_*, RECOVERY_EXECUTED, RECOVERY_VERIFIED, INCIDENT_RESOLVED)
 * have actually been emitted for this incident. If none of those exist yet
 * (investigation still running, or it abstained), this shows an honest
 * neutral empty state instead of implying recovery is "pending" for an
 * incident that will never trigger it.
 */
export function RecoveryPanel({ incident, events }: RecoveryPanelProps) {
  const { recovery_plan: plan, approval_state: approval, action_history: actions, decision } = incident;
  const recoveryEvents = events.filter((e) =>
    RECOVERY_STEP_TYPES.some((step) => step.type === e.event_type),
  );
  const queryClient = useQueryClient();
  const [approvedBy, setApprovedBy] = useState("operator");
  const approveMutation = useMutation({
    mutationFn: (decisionValue: "APPROVED" | "REJECTED") =>
      approveRecoveryPlan(incident.incident_id, decisionValue, approvedBy.trim() || "operator"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["incident", incident.incident_id] });
      queryClient.invalidateQueries({ queryKey: ["incident-events", incident.incident_id] });
    },
  });

  if (!plan && recoveryEvents.length === 0) {
    return (
      <GlassSurface light className={styles.empty}>
        <StatusDot tone="neutral" />
        <span>
          {decision?.outcome === "ABSTAINED"
            ? "No recovery action — investigation abstained without a supported diagnosis."
            : "Recovery is proposed automatically if the investigation reaches a diagnosis."}
        </span>
      </GlassSurface>
    );
  }

  return (
    <motion.div initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ type: "spring", stiffness: 240, damping: 30 }}>
      <GlassSurface elevation="raised" className={styles.wrap}>
        <div className={styles.header}>
          <span className={styles.title} title="Deterministic safety layer validates every proposed action before execution; nothing runs without human approval.">
            Recovery
          </span>
          {plan && <Badge tone={plan.risk_level === "HIGH" ? "red" : plan.risk_level === "MEDIUM" ? "amber" : "green"}>{plan.risk_level} risk</Badge>}
        </div>

        {incident.status === "RESOLVED" && (
          <div className={styles.resolvedBanner}>
            <StatusDot tone="green" />
            Incident resolved — recovery verified.
          </div>
        )}

        {recoveryEvents.length > 0 && (
          <div className={styles.stepList}>
            {recoveryEvents.map((e) => (
              <div key={e.event_id} className={styles.step}>
                <StatusDot
                  tone={
                    e.event_type === "HUMAN_APPROVAL_REJECTED" || e.status === "expired"
                      ? "red"
                      : e.event_type === "RECOVERY_PROPOSED"
                        ? "neutral"
                        : "green"
                  }
                />
                <span className={styles.stepLabel}>
                  {RECOVERY_STEP_TYPES.find((s) => s.type === e.event_type)?.label ?? e.event_type}
                </span>
                <span className={styles.stepDetail}>{e.source}</span>
                <Timestamp iso={e.timestamp} />
              </div>
            ))}
          </div>
        )}

        {plan && (
          <div className={styles.plan}>
            <div className={styles.planMeta}>
              <MonoLabel>{plan.plan_id}</MonoLabel>
              {plan.blast_radius && <span>blast radius: {plan.blast_radius}</span>}
            </div>
            <div className={styles.actionList}>
              {plan.actions.map((action, i) => (
                <div key={`${action.action}-${i}`} className={styles.actionRow}>
                  <MonoLabel>{action.action}</MonoLabel>
                  {action.rationale && <span className={styles.actionRationale}>{action.rationale}</span>}
                </div>
              ))}
            </div>
          </div>
        )}

        {approval && (
          <div className={styles.actionRow}>
            <Badge tone={approvalDecisionTone(approval.decision)}>{approval.decision}</Badge>
            {approval.approved_by && <span className={styles.actionRationale}>by {approval.approved_by}</span>}
            {approval.reason && <span className={styles.actionRationale}>{approval.reason}</span>}
          </div>
        )}

        {approval?.decision === "PENDING" && (
          <div className={styles.approvalRow}>
            <input
              className={styles.approverInput}
              value={approvedBy}
              onChange={(e) => setApprovedBy(e.target.value)}
              placeholder="your name"
              aria-label="Approver name"
            />
            <button
              className={styles.approveBtn}
              disabled={approveMutation.isPending}
              onClick={() => approveMutation.mutate("APPROVED")}
            >
              Approve
            </button>
            <button
              className={styles.rejectBtn}
              disabled={approveMutation.isPending}
              onClick={() => approveMutation.mutate("REJECTED")}
            >
              Reject
            </button>
          </div>
        )}

        {actions.length > 0 && (
          <div className={styles.actionList}>
            {actions.map((a, i) => (
              <div key={`${a.action}-${i}`} className={styles.actionRow}>
                <Badge tone={actionStatusTone(a.status)}>{a.status}</Badge>
                <MonoLabel>{a.action}</MonoLabel>
                {a.detail && <span className={styles.actionRationale}>{a.detail}</span>}
                <Timestamp iso={a.timestamp} />
              </div>
            ))}
          </div>
        )}
      </GlassSurface>
    </motion.div>
  );
}
