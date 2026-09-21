// Static, non-data explanation of the Command Center's seven questions.
// Shown only while agents are OFF and labelled illustrative there. It states
// what each card shows — it deliberately contains no incident, metric, ID or
// evidence, so it can never be mistaken for live telemetry.
export const SEVEN_QUESTIONS = [
  {
    n: "01",
    question: "What happened?",
    shows: "The symptom that was reported, when it was reported, and where the incident stands now.",
  },
  {
    n: "02",
    question: "What is NEXUS doing?",
    shows: "Which of the 7 agents is working right now, with status taken from real events as they arrive.",
  },
  {
    n: "03",
    question: "What evidence did it find?",
    shows: "What each agent reported after running its system checks, and which findings point toward, against, or are still missing.",
  },
  {
    n: "04",
    question: "What does it currently believe?",
    shows: "The leading possible cause in one sentence, with the confidence the Evidence Agent reported.",
  },
  {
    n: "05",
    question: "Did it challenge itself?",
    shows: "The Root-Cause Critic's verdict — supported, not proven yet, or contradicted — and the assumptions it could not verify.",
  },
  {
    n: "06",
    question: "What did it decide?",
    shows: "Either a supported root cause or an explicit abstention with reasons. NEXUS is allowed to decline to guess.",
  },
  {
    n: "07",
    question: "Can it recover?",
    shows: "A bounded recovery plan, offered only after a supported diagnosis. A human must approve before anything runs.",
  },
] as const;
