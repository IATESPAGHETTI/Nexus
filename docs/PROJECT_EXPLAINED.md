# NEXUS, explained in plain English

NEXUS = **Autonomous Multi-Agent Production Failure Investigation & Recovery System**.
Built by Deepu (academic team: Deepu, Mukund, Vanshika). This page is for anyone who
needs to understand or present the project without knowing the code.

## 1. The one-minute version

When a website breaks, engineers get paged, dig through graphs and logs, argue about
the cause, and then try a fix. NEXUS imitates that with a **team of AI agents**:

1. Something breaks (we break a *simulated* shop on purpose).
2. Four specialist agents each inspect one kind of evidence.
3. A fifth agent turns the evidence into possible causes.
4. A sixth agent (the **Critic**) tries to prove those causes wrong.
5. If one cause survives, a seventh agent proposes a fix.
6. Safety rules check the fix, **a human must approve it**, it runs, and NEXUS
   re-measures the service to see whether it really worked.
7. If the evidence isn't good enough, NEXUS says **"I don't know"** (abstains)
   instead of guessing.

Everything is shown live on a dashboard.

**Hospital analogy:** the specialists are lab technicians, the Evidence Agent is the
doctor forming a diagnosis, the Critic is a second doctor asking "are you sure?", the
Recovery Agent suggests a treatment, and the hospital rules plus the patient's consent
(human approval) decide whether it's given.

## 2. Where the data comes from

NEXUS never touches real company data. It investigates a **simulated online shop**
(`production/`): 10 invented orders in a small database, plus metrics, logs and traces
produced by real requests to that shop. `fault_injection/` then breaks it on purpose in
one of 5 ways:

| Fault | What really happens in the simulator |
|---|---|
| Bad deployment | A new version makes ~35% of order requests fail |
| Database slowdown | Every query is delayed by 0.25 s |
| Config error | A bad setting makes every order request fail |
| Dependency failure | A downstream service stops answering order lookups |
| Resource exhaustion | Everything gets slower and some requests fail |

Because we cause the fault, we know the right answer ("ground truth"), so the AI can be
graded. The answer key is hidden from the agents; only the evaluation code reads it.
The shop's own control calls (`/admin/*`) are hidden from the agents' metrics, logs and
traces. The Change Analysis Agent no longer reads this repository's code history (that tool is
disabled), because the history contains the simulator's fault switches and would give the answer away.

This shows the *method* works on a controlled toy system. It is not proof it works on a
real company's systems.

## 3. The team

| Agent | Job | Tools it may use |
|---|---|---|
| Incident Manager | Coordinates; not an AI chat, just the conductor | none |
| Metrics Agent | Request counts, speed, errors | `get_metrics` |
| Logs & Traces Agent | What happened, when | `query_logs`, `get_trace` |
| Change Analysis Agent | Did a deployment or config change cause it? | `get_recent_deployments`, `get_git_diff` |
| Database Agent | Is the database healthy? | `get_database_stats` |
| Evidence Agent | Turns evidence into ranked possible causes | none (reads what others found) |
| Root-Cause Critic | Looks for contradictions and unsupported assumptions | none |
| Recovery Agent | Proposes a bounded fix | none (it can only *suggest*) |

Rules that keep it honest:
- Agents can only learn things through their tools, and the tools return real data from
  the simulator. An agent can't just guess.
- The Evidence Agent and Critic have **no tools**; they only reason about evidence
  already collected. An evidence id they invent is dropped by code.
- The Recovery Agent can't run anything. Only the separate guardrails code can.

## 4. Two protocols (the "real, not fake" part)

- **MCP (Model Context Protocol):** a standard way to give an AI a set of tools. NEXUS
  has a real MCP server with 7 read-only diagnostic tools (`get_metrics`, `query_logs`,
  `get_trace`, `get_recent_deployments`, `get_git_diff`, `get_database_stats`,
  `run_diagnostic`).
- **A2A (Agent-to-Agent protocol):** a standard way for separate AI services to message
  each other. Each of the 7 agents runs as its **own separate program on its own port**
  (8101-8107). The Incident Manager reaches them over the network, not by calling
  Python functions. That's what makes it genuine A2A, and you can see each agent's
  "business card" at `http://localhost:810X/.well-known/agent-card.json`.

## 5. The investigation loop

```
incident -> 4 specialists gather evidence (in parallel, over A2A, using MCP tools)
         -> Evidence Agent proposes causes with confidence + supporting evidence
         -> Critic challenges the top cause
              SUPPORTED          -> diagnosis reached
              CONTRADICTED       -> reject it, try the next cause
              NOT ENOUGH EVIDENCE-> ask specialists for more, try again
              ABSTAIN            -> stop, say "unknown"
         -> repeat at most 3 rounds (MAX_REEVALUATION_LOOPS), then abstain
```

It never forces an answer just to finish. There are also **spending limits** per
investigation (max model calls, max tokens, max tokens per agent). When one is hit, NEXUS
stops and abstains, naming the limit. Usage is measured from what each agent reports,
and shown on the dashboard.

## 6. Recovery is deliberately cautious

```
diagnosis -> Recovery Agent proposes a plan
          -> safety validation (allowed actions only, max 3 actions, no HIGH risk,
             must describe a rollback, and must be able to fix the symptom the
             evidence actually shows)
          -> a HUMAN clicks Approve (or Reject)
          -> guardrails run it (kill switch checked before every action)
          -> live check: send real requests, is it fast and error-free now?
          -> RESOLVED only if that check passes; otherwise "not verified"
```

The only actions that exist: `restart_service`, `rollback_deployment`, `reset_config`,
`scale_resources`. No AI-written shell commands are ever executed.

## 7. What you see on the dashboard

Live agent status, the messages between agents (A2A), every tool call (MCP), a timeline,
the possible causes with their evidence, the Critic's challenge, the decision, the
recovery plan with Approve/Reject, and model usage against the limits. The **agent
switch** (ON) really starts the 7 agent services.

## 8. How it is tested

- Automated tests that need no AI: control flow, safety rules, budget limits, storing
  incidents, the guardrails, the simulator's faults.
- Tests with the real protocols and a real model, run when a working key is available.
- A planned benchmark comparing (a) one AI alone, (b) the full team, (c) the team
  **without** the Critic, on the same 5 faults, scored against the hidden answer key.
- Incidents are saved in a SQLite file, so they survive a restart.

## 9. Honest status and limits

- The simulator is a toy; results don't prove anything about real production systems.
- The 3-way benchmark is built but **has not been run to completion**, so there are no
  accuracy numbers yet. Don't quote any.
- The model is DeepSeek by default (Groq and Gemini are optional). It is not the model
  the original brief named (GPT-OSS 120B on Groq).
- In one live run the Recovery Agent picked a fix that didn't match the problem and the
  live check correctly said "not verified". A guardrail was added afterwards to reject
  such plans; that new guardrail has been unit-tested but not yet exercised with a live
  model.
- Recovery and post-fix verification model calls aren't counted toward the budget yet.
- Live run 2026-10-12 (DeepSeek, slow database): diagnosed in about 48 s, proposed the correct fix
  (`scale_resources`), measured 22 model calls / 81,486 tokens. Execution and the live
  verification were not re-run in that pass (it stopped at human approval).
- Detection of "does this fix fit the symptom" covers 4 symptom types only.

## 10. Words you may be asked about

- **Package:** ready-made code someone else wrote that you install (e.g. `fastapi`,
  `google-adk`) instead of writing it yourself. Each part of NEXUS lists its packages in
  its own `requirements.txt` and installs them in its own separate environment so one
  part can't break another.
- **Hypothesis:** a possible cause, with the evidence for and against it.
- **Ground truth:** the known correct cause, because we injected the fault ourselves.
- **Abstain:** deliberately answering "not enough evidence" instead of guessing.
- **Pull request:** a proposal to merge your changes into the main code, reviewed by
  others before it goes live. NEXUS's "human approves before the fix runs" mirrors it.

## 11. Where to look

| Question | File |
|---|---|
| How it is built | `docs/ARCHITECTURE.md`, `docs/NEXUS_OVERVIEW.md` |
| Data shapes / API | `docs/API_CONTRACT.md`, `docs/EVENT_SCHEMA.md` |
| How it is graded | `docs/EVALUATION.md` |
| Run the demo | `docs/DEMO_RUNBOOK.md` |
| Current status | `docs/PROJECT_STATE.md` |

## Update 2026-10-13: five failures, and not every agent is called

- The demo can break the shop five ways: slow database, bad release, wrong setting, payment service down, out of memory.
  NEXUS only hears a customer-style complaint, never the cause.
- **Triage:** like an on-call lead choosing who to page, the Incident Manager calls only the specialists the complaint
  points at. If the Critic later asks for something a skipped specialist covers, that specialist is called next round.
- **Fixes it chooses between** (never code changes, only a fixed menu a person approves): restart, roll back to the
  previous version, reset configuration, restore resources.
- **What testing taught us:** the logs now record the real error message; a safety check rejects fixes that cannot
  work; the Critic is told what evidence can exist; the Logs agent is capped at four tool calls; each demo starts from a
  clean shop. All are listed on the presentation page under "What testing taught us".
- **Honest limit:** each failure was run once after the fixes (all five fixed and verified). That is a smoke test, not a
  benchmark.