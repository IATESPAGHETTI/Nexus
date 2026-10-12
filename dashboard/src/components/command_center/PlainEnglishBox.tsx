import { useMemo } from "react";
import type { IncidentState, NexusEvent } from "../../api/types";
import { AGENT_WORDS, NEXUS_WORDS, wordsUsedIn, type GlossaryEntry } from "../../lib/glossary";
import { countEvents, type CommandCenterModel } from "../../lib/presentation";
import styles from "./PlainEnglishBox.module.css";

interface Props {
  model: CommandCenterModel;
  incident: IncidentState;
  events: NexusEvent[] | undefined;
}

function plural(n: number, one: string, many = `${one}s`): string {
  return `${n} ${n === 1 ? one : many}`;
}

/** Every sentence below states a count or a recorded outcome from the real incident. */
function buildStory(model: CommandCenterModel, events: NexusEvent[] | undefined): string[] {
  const counts = countEvents(events);
  const story: string[] = [];

  story.push(`The problem: "${model.description}" NEXUS opened an incident and started investigating.`);

  if (counts.a2a === 0 && counts.mcp === 0) {
    story.push("No agent has done anything yet, so there is nothing more to explain.");
    return story;
  }

  story.push(
    `It split the work. Four specialist agents each looked at one angle of the shop (speed numbers, request logs, recent changes, the database). Together they ran ${plural(counts.mcp, "system check")} and the Incident Manager exchanged ${plural(counts.a2a, "message")} with the agents so far. Think of detectives who each report back to one lead.`,
  );

  if (model.belief) {
    story.push(
      `A fifth agent, the Evidence Agent, put the findings together and wrote down a guess about what is broken, with its own confidence of ${model.belief.confidencePct}%. A guess is only a guess until it is checked.`,
    );
  }

  if (model.challenge) {
    const outcome =
      model.challenge.verdict === "SUPPORTED"
        ? "it could not knock the guess down, so the guess stands"
        : model.challenge.verdict === "ABSTAIN"
        ? "it advised NEXUS not to commit to an answer"
        : `its verdict was “${model.challenge.verdictLabel.toLowerCase()}”`;
    story.push(
      `A sixth agent, the Root-Cause Critic, then tried to prove that guess wrong. It reviewed it ${plural(model.challenge.reviews, "time")}; ${outcome}. This is the safeguard against a confident but wrong answer.`,
    );
  }

  const d = model.decision;
  if (d.kind === "ABSTAINED") {
    story.push("Decision: NEXUS chose NOT to guess. When the proof is not strong enough it stops and tells a person, and it changes nothing on the shop.");
  } else if (d.kind === "DIAGNOSED" || d.kind === "RESOLVED") {
    story.push(
      `Decision: the cause was supported${d.loopsUsed != null ? ` after ${plural(d.loopsUsed, "review round")}` : ""}, so the seventh agent (Recovery Agent) proposed a limited fix.`,
    );
  }

  const r = model.recovery;
  if (r) {
    const act = r.actions.map((a) => a.label.toLowerCase()).join(" and ") || "no allowed action";
    story.push(`The proposed fix: ${act}. Safety rules checked it first, and it only runs if a person clicks Approve. Risk was rated ${r.risk.toLowerCase()}.`);
    if (r.stage === "AWAITING_APPROVAL") story.push("Right now NEXUS is waiting for you. Nothing has been changed.");
    else if (r.stage === "EXPIRED") story.push("The approval window passed, so nothing ran. The plan is saved and can still be approved.");
    else if (r.stage === "DECLINED") story.push("A person declined the plan, so nothing was changed.");
    else if (r.stage === "REJECTED_BY_SAFETY") story.push("The safety rules refused this plan, so nothing was changed.");
    else if (r.stage === "EXECUTING" || r.stage === "VERIFYING") story.push("A person approved it. NEXUS is carrying it out and measuring the shop now.");
    else if (r.verification) {
      const checks = r.verification.checks
        .map((c) => `${c.path} answered in ${c.medianMs} ms`)
        .join(" and ");
      story.push(
        r.stage === "RECOVERED"
          ? `Proof: after the fix NEXUS sent real test requests to the shop. ${checks}, under the ${r.verification.limitMs} ms limit. Only then was the incident called recovered.`
          : `The fix ran, but the check was not good enough (${checks}; limit ${r.verification.limitMs} ms), so the incident stays open.`,
      );
    }
  }
  return story;
}

function collectText(model: CommandCenterModel): string {
  const parts: string[] = [
    model.belief?.statement ?? "",
    ...model.findings.map((f) => f.text),
    ...(model.belief?.missing ?? []),
    model.challenge?.rationale ?? "",
    ...(model.challenge?.alternatives ?? []),
    ...(model.challenge?.assumptions ?? []),
    ...(model.challenge?.requested ?? []),
    ...(model.recovery?.actions.flatMap((a) => [a.label, a.rationale ?? ""]) ?? []),
    model.recovery?.blastRadius ?? "",
    model.recovery?.rollbackPlan ?? "",
  ];
  return parts.join("\n");
}

function Glossary({ title, hint, entries }: { title: string; hint: string; entries: GlossaryEntry[] }) {
  if (!entries.length) return null;
  return (
    <div className={styles.glossBlock}>
      <div className={styles.glossTitle}>{title}</div>
      <div className={styles.glossHint}>{hint}</div>
      <dl className={styles.gloss}>
        {entries.map((e) => (
          <div key={e.term} className={styles.glossItem}>
            <dt>{e.term}</dt>
            <dd>{e.plain}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

export function PlainEnglishBox({ model, incident, events }: Props) {
  const story = useMemo(() => buildStory(model, events), [model, events]);
  const used = useMemo(() => wordsUsedIn(collectText(model)), [model]);
  const notUsed = AGENT_WORDS.length - used.length;

  return (
    <section id="plain-english" className={styles.box} aria-label="Plain English explanation">
      <div className={styles.kicker}>IN PLAIN ENGLISH</div>
      <h3 className={styles.h}>What all of this means, without the jargon</h3>

      <ol className={styles.story}>
        {story.map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ol>

      <div className={styles.cols}>
        <Glossary
          title="Technical words in this incident"
          hint={
            used.length
              ? `The agents used these words in the text above (${incident.incident_id}). Only words that really appear are listed.`
              : ""
          }
          entries={used}
        />
        <Glossary title="NEXUS words" hint="The vocabulary of this screen." entries={NEXUS_WORDS} />
      </div>
      {used.length === 0 && (
        <p className={styles.none}>
          The agents have not written any technical text yet, so there is nothing extra to translate. {notUsed > 0 ? "Words appear here as they use them." : ""}
        </p>
      )}
    </section>
  );
}
