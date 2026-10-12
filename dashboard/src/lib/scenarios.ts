// The failures the demo can inject. `symptom` is what the agents are told: only
// what a customer would notice, never the cause (blind-evaluation rule in
// fault_injection/CLAUDE.md). The Incident Manager's triage reads this text to
// decide which agents are worth calling, so different symptoms wake different agents.

export interface DemoScenario {
  id: string;
  label: string;
  /** one line for the viewer: what breaks in the shop */
  blurb: string;
  symptom: string;
}

export const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: "db_slowdown",
    label: "Slow database",
    blurb: "Every order lookup becomes slow, but nothing errors.",
    symptom: "Customers report that order requests are responding slowly. Investigate the cause.",
  },
  {
    id: "bad_deployment",
    label: "Bad release",
    blurb: "A new version ships with a bug, so some orders fail.",
    symptom: "Orders suddenly started failing with errors for some customers. Investigate the cause.",
  },
  {
    id: "config_error",
    label: "Wrong setting",
    blurb: "An invalid setting makes every order request fail.",
    symptom: "Every order request is failing with an error right now. Investigate the cause.",
  },
  {
    id: "dependency_failure",
    label: "Payment service down",
    blurb: "A service the shop depends on stops answering.",
    symptom: "Looking up a single order takes a long time and then fails. Investigate the cause.",
  },
  {
    id: "resource_exhaustion",
    label: "Out of memory",
    blurb: "The whole shop slows down and starts refusing requests.",
    symptom: "The whole shop is getting slower and sometimes refuses requests. Investigate the cause.",
  },
];

export function scenarioById(id: string): DemoScenario {
  return DEMO_SCENARIOS.find((s) => s.id === id) ?? DEMO_SCENARIOS[0];
}
