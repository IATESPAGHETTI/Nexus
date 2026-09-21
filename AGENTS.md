# NEXUS — Codex MASTER INSTRUCTIONS

> **Project:** NEXUS
> **Full title:** Autonomous Multi-Agent Production Failure Investigation & Recovery System
> **Primary developer:** Deepu
> **Academic team:** Deepu, Mukund, Vanshika
> **Runtime LLM:** GPT-OSS 120B via Groq
> **Agent framework:** Google ADK (Python), subject to the spike gate below
> **Communication:** Real A2A, not cosmetic/internal function calls
> **Tools:** MCP diagnostic tools
> **Deployment:** Docker Compose
> **Backend:** Python + FastAPI
> **Dashboard:** React-based live investigation UI

---

## 1. PURPOSE

NEXUS is a controlled academic research/demo system for autonomous production-failure investigation and bounded recovery.

The system must demonstrate:

1. A production-like software failure is injected.
2. An Incident Manager creates and maintains incident state.
3. Specialized agents gather independent evidence.
4. Agents communicate through genuine A2A.
5. Agents use MCP diagnostic tools to access controlled evidence.
6. An Evidence Agent forms explicit candidate hypotheses.
7. A Root-Cause Critic challenges hypotheses and searches for contradictions.
8. The system requests missing evidence and re-evaluates.
9. The system either reaches a supported diagnosis or explicitly abstains.
10. A Recovery Agent proposes a bounded recovery plan.
11. Recovery requires validation and human approval.
12. The entire investigation is observable through a dashboard.
13. Fault injection and quantitative evaluation are repeatable.

This is **not a generic chatbot**.

---

# 2. NON-NEGOTIABLE RULES

## 2.1 Do not fake functionality

Never create cosmetic implementations that merely claim to be:

- A2A
- MCP
- multi-agent
- autonomous reasoning
- recovery
- evaluation
- observability

If a feature is described as implemented, it must actually work and have a test or reproducible verification.

In particular:

> Do not label Python function calls between agents as A2A.

NEXUS must use actual agent-to-agent communication that can be demonstrated and inspected.

---

## 2.2 Preserve working functionality

Before changing an existing component:

1. Read its local `AGENTS.md`.
2. Read only the relevant documentation.
3. Inspect the specific implementation.
4. Run the relevant tests.
5. Make the smallest safe change.
6. Re-run tests.
7. Update `docs/PROJECT_STATE.md`.

Never rewrite working Phase 1/2 infrastructure merely for stylistic reasons.

---

## 2.3 Never claim untested work is complete

Use precise language:

- `implemented + tested`
- `implemented + not yet tested`
- `planned`
- `blocked`
- `partially implemented`

Do not say "works" without actually verifying it.

---

# 3. CONTEXT-EFFICIENCY RULES

NEXUS is intentionally structured so Codex does **not** need to load the whole repository into every context window.

## 3.1 Durable memory hierarchy

Use:

```text
Root AGENTS.md
    ↓
Local folder AGENTS.md
    ↓
docs/PROJECT_STATE.md
    ↓
Relevant architecture/API/event docs
    ↓
Only the source files needed for the current task
```

The filesystem is the durable project memory.

The conversation context is NOT the project database.

## 3.2 Never repeatedly read the whole repository

Do NOT:

- recursively read every source file at the beginning of every task
- dump the whole repository into context
- repeatedly reread unchanged documentation
- use the runtime application database as Codex's development memory

When working on one component, read:

1. root `AGENTS.md`
2. that component's local `AGENTS.md`
3. `docs/PROJECT_STATE.md`
4. only relevant contracts/docs
5. only relevant source files

## 3.3 Local AGENTS.md files

Major folders should contain a local `AGENTS.md`.

Each local file should explain:

- purpose
- responsibilities
- interfaces
- dependencies
- testing commands
- important constraints
- what must not be changed
- current implementation status

Keep local files short.

## 3.4 PROJECT_STATE.md

`docs/PROJECT_STATE.md` is the compact current project memory.

After every meaningful phase:

- update completed work
- record tests
- record known limitations
- record current phase
- record next action
- record architectural decisions

Do not turn it into a giant diary.

If context becomes large, save durable progress there and continue from the files.

---

# 4. DEVELOPMENT OWNERSHIP

**NEXUS is being built by Deepu alone.**

Mukund and Vanshika are academic team members listed for the project submission, but they are NOT active developers unless Deepu explicitly provides evidence of a real contribution.

Therefore:

- Treat Deepu as the sole active technical owner.
- Never fabricate contributions by Mukund or Vanshika.
- Never assign implementation, testing, commits, architecture, or documentation to them unless they actually did it.
- Submission-facing documents may retain the academic team names where required.
- Technical progress reports must describe actual work completed.
- If a real contribution occurs later, document only the verified contribution.

---

# 5. CURRENT VERIFIED STATE

At the time these instructions were written:

## Phase 1 — Foundation

**Completed and verified.**

Includes:

- NEXUS repository scaffold
- FastAPI backend
- simulated production service
- Docker Compose
- tests
- root/local AGENTS.md structure
- architecture/API/event/evaluation documentation
- PROJECT_STATE.md

Docker Compose was built and started successfully and the health endpoints were verified.

## Phase 2 — Observability

**Completed and verified.**

The production simulation now includes real controlled evidence sources for:

- metrics
- logs
- traces
- database diagnostics
- change/deployment history
- order/query activity

The Phase 2 test suite passed **8/8** and the real Docker container was tested end-to-end.

Do not unnecessarily modify this working foundation.

## Phase 3+

Not yet considered complete.

Before substantial Phase 3 implementation, the ADK/Groq spike described below must pass.

---

# 6. RUNTIME LLM

NEXUS must use:

```text
GPT-OSS 120B
        ↓
      Groq
```

The runtime model is NOT:

- Anthropic Codex
- Gemini
- OpenAI hosted GPT

Codex may be used to BUILD NEXUS, but Codex is completely separate from the LLM that NEXUS uses at runtime.

Do not confuse:

```text
Codex
= development agent

GPT-OSS 120B via Groq
= NEXUS runtime reasoning model
```

---

# 7. GROQ SECRET MANAGEMENT

The real key must live only in the local root `.env`.

Expected:

```env
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b
```

Rules:

- Never print the API key.
- Never log the API key.
- Never put the API key in source code.
- Never put the API key in AGENTS.md.
- Never put the API key in documentation.
- Never commit `.env`.
- Keep `.env` in `.gitignore`.
- `.env.example` may contain variable names but never the real secret.
- Never ask Deepu to paste the secret into source files.

If a secret accidentally appears in output, stop and redact it.

---

# 8. GROQ USAGE / TOKEN VISIBILITY

NEXUS must eventually provide a visible runtime LLM usage panel.

The dashboard should expose, where the provider/API makes the information available:

- tokens used
- remaining token quota
- requests used
- remaining request quota
- rate-limit information
- reset timing
- per-incident usage
- per-agent usage
- cumulative session usage
- warnings when quota is approaching a configured threshold

Do not invent quota numbers.

If Groq exposes rate-limit information through response headers/API metadata, capture it safely.

If an exact quota is not available from the API response, display:

```text
Unavailable from provider
```

rather than guessing.

Never display the API key.

The system should also implement application-level budgets so a runaway investigation cannot waste the entire free quota.

Suggested controls:

```text
MAX_TOKENS_PER_AGENT
MAX_LLM_CALLS_PER_INCIDENT
MAX_TOTAL_TOKENS_PER_INCIDENT
MAX_REEVALUATION_LOOPS
```

Values should be configurable through environment variables/configuration rather than hardcoded throughout the codebase.

---

# 9. AGENT FRAMEWORK — GOOGLE ADK

The current architectural direction is **Google ADK for Python**.

However, ADK migration is gated by a mandatory compatibility spike.

Do NOT blindly migrate the project.

## 9.1 Mandatory spike

Before substantial Phase 3/4/5 agent implementation:

Create a minimal ADK proof of concept that:

1. creates one ADK agent
2. uses GPT-OSS 120B through Groq via the supported Python/LiteLLM integration
3. gives the agent one trivial tool
4. invokes the agent
5. verifies the model actually responds
6. verifies the model actually performs a tool call
7. verifies the tool result reaches the model
8. records exact dependency versions
9. confirms the model identifier actually used
10. confirms Phase 1/2 tests still pass

Do not build the real agents until this passes.

If the spike fails:

- diagnose the failure
- do not silently substitute another model
- do not silently substitute Anthropic/Gemini
- document the failure
- propose alternatives
- preserve the verified Phase 1/2 system

---

# 10. A2A IS A HARD REQUIREMENT

Real A2A is mandatory.

The final architecture must demonstrate actual agent-to-agent communication.

Preferred architecture:

```text
                 Incident Manager
                        │
            ┌───────────┼───────────┐
            │           │           │
           A2A         A2A         A2A
            ↓           ↓           ↓
        Metrics       Logs        Change
         Agent        Agent        Agent
            │           │           │
            └───────────┼───────────┘
                        ↓
                  Evidence Agent
                        ↓
                 Root-Cause Critic
                        ↓
                  A2A challenge
                        ↓
                 Re-investigation
                        ↓
               Diagnosis / Abstention
```

The exact process topology must be decided deliberately.

Strongest demonstration:

```text
Agent A = independent service/process
Agent B = independent service/process
Agent A → real A2A protocol → Agent B
Agent B → MCP tools → evidence
Agent B → A2A response → Agent A
```

If ADK provides the protocol/server/client machinery, use it rather than reimplementing the A2A protocol.

Do not claim "genuine A2A" merely because separate ADK agent objects exist in the same Python process.

If the academic grading requirement is ambiguous, prefer the independently addressable service/process design because it is easier to demonstrate.

---

# 11. MCP IS A HARD REQUIREMENT

NEXUS must have actual MCP diagnostic tools.

Planned tools include:

```text
get_metrics
query_logs
get_trace
get_recent_deployments
get_git_diff
get_database_stats
run_diagnostic
```

The MCP layer should expose controlled access to the simulated production environment.

Agents should not directly rummage through arbitrary files or databases when an appropriate MCP diagnostic tool exists.

MCP tools should return structured, bounded evidence.

---

# 12. EVIDENCE-FIRST DESIGN

Agents must investigate using evidence.

Do not let the LLM simply guess a root cause from the incident description.

Evidence should flow like:

```text
Incident
   ↓
Tool calls
   ↓
Observations
   ↓
Evidence
   ↓
Hypothesis
   ↓
Criticism
   ↓
Additional evidence
   ↓
Re-evaluation
   ↓
Supported diagnosis OR abstention
```

Every hypothesis should track:

- hypothesis ID
- statement
- supporting evidence IDs
- contradicting evidence IDs
- confidence/rationale as structured data
- missing evidence
- requesting agent
- status
- timestamps
- revision history

---

# 13. ROOT-CAUSE CRITIC

The critic is a mandatory component.

It must not simply agree with the Evidence Agent.

For each leading hypothesis, the critic should:

1. inspect supporting evidence
2. search for contradictions
3. identify unsupported assumptions
4. request missing evidence
5. propose discriminating diagnostic actions
6. return a structured challenge
7. cause re-evaluation when appropriate

Possible outcomes:

```text
SUPPORTED
CONTRADICTED
INSUFFICIENT_EVIDENCE
REQUEST_MORE_EVIDENCE
ABSTAIN
```

Do not expose private model chain-of-thought.

The dashboard should show structured artifacts:

```text
Observation
Evidence
Hypothesis
Supporting evidence
Contradicting evidence
Critic challenge
Requested evidence
Decision
```

---

# 14. RE-EVALUATION LOOP

The central reasoning loop is:

```text
Hypothesis
    ↓
Root-Cause Critic
    ↓
Does evidence support it?
    ├── Yes → diagnosis candidate
    ├── No → reject/revise
    └── Missing evidence → request evidence
                              ↓
                         specialized agent
                              ↓
                           MCP tool
                              ↓
                         new evidence
                              ↓
                         update hypothesis
                              ↓
                            critic
```

Bound the loop.

Never allow an infinite autonomous loop.

Use:

```text
MAX_REEVALUATION_LOOPS
```

and an explicit abstention/escalation path.

---

# 15. INCIDENT STATE

Incident state must be explicit and persistent.

At minimum:

```text
incident_id
status
created_at
updated_at
timeline
evidence
agent_findings
agent_messages
hypotheses
critic_results
experiments
recovery_plan
approval_state
action_history
token_usage
```

The runtime database is application state.

It is NOT Codex's development memory.

---

# 16. EVENT CONTRACT

Every important investigation transition must emit a structured event.

Minimum event categories:

```text
INCIDENT_CREATED
AGENT_STARTED
AGENT_COMPLETED
A2A_REQUEST
A2A_RESPONSE
MCP_TOOL_CALL
MCP_TOOL_RESULT
EVIDENCE_ADDED
HYPOTHESIS_CREATED
HYPOTHESIS_UPDATED
CRITIC_CHALLENGE
RE_EVALUATION_STARTED
RE_EVALUATION_COMPLETED
DIAGNOSIS_REACHED
ABSTENTION
RECOVERY_PROPOSED
SAFETY_VALIDATION
HUMAN_APPROVAL_REQUESTED
HUMAN_APPROVAL_GRANTED
RECOVERY_EXECUTED
RECOVERY_VERIFIED
INCIDENT_RESOLVED
```

Example:

```json
{
  "event": "A2A_REQUEST",
  "timestamp": "2026-01-01T12:00:00Z",
  "from": "evidence_agent",
  "to": "root_cause_critic",
  "incident_id": "INC-042",
  "message": {
    "type": "HYPOTHESIS_REVIEW_REQUEST",
    "hypothesis_id": "H1"
  }
}
```

The dashboard must receive these events through a backend event stream.

---

# 17. LIVE DASHBOARD

The dashboard is not decoration.

It must make the investigation understandable during the final demo.

Required views:

## Investigation graph

Show:

- Incident Manager
- Metrics Agent
- Logs/Traces Agent
- Change Analysis Agent
- Database Agent
- Evidence Agent
- Root-Cause Critic
- Recovery Agent

Show animated/live handoffs.

## Agent cards

Each agent should expose structured status such as:

```text
IDLE
RUNNING
WAITING
COMPLETED
FAILED
```

and:

- current action
- MCP tool
- findings count
- evidence count
- status
- token usage

## A2A communication panel

Show:

```text
timestamp
sender
recipient
message type
incident ID
status
```

This is especially important for proving genuine A2A.

## MCP panel

Show:

```text
agent
tool
arguments summary
start time
duration
result summary
```

Never display secrets.

## Timeline

Show all major investigation events chronologically.

## Hypothesis panel

Show:

- hypothesis
- supporting evidence
- contradictory evidence
- critic challenge
- requested evidence
- current status

## LLM usage panel

Show available Groq usage/rate-limit information and NEXUS's application-level token/call budgets.

---

# 18. PRODUCTION SIMULATION

The simulated production service is the controlled environment.

It should remain:

- deterministic where practical
- observable
- fault-injectable
- isolated
- safe

Potential incident classes:

```text
database slowdown
bad deployment
configuration error
dependency failure
resource exhaustion
```

Do not connect NEXUS to real production systems.

---

# 19. FAULT INJECTION

Fault injection must be controlled and repeatable.

Each scenario needs:

```text
scenario_id
description
fault_type
injection_method
expected_symptoms
ground_truth_root_cause
recovery_expectation
```

The evaluator must know the ground truth without exposing it to the agents during blind evaluation.

---

# 20. RECOVERY SAFETY

Recovery must never be an unrestricted autonomous action.

Required flow:

```text
Diagnosis
   ↓
Recovery Agent
   ↓
Bounded recovery plan
   ↓
Safety validation
   ↓
Human approval
   ↓
Sandbox/controlled execution
   ↓
Verification
   ↓
Resolved / failed / escalated
```

Guardrails should include:

- allowlists
- rate limits
- blast-radius controls
- sandbox restrictions
- kill switch
- human approval
- action logging

Never execute arbitrary shell commands generated by an LLM.

---

# 21. EVALUATION

NEXUS must be evaluated scientifically rather than only demonstrated visually.

Measure:

- root-cause accuracy
- evidence accuracy
- false diagnosis rate
- abstention correctness
- diagnosis time
- remediation success
- tool cost
- token cost
- A2A behavior
- critic effectiveness

Compare:

1. single-agent baseline
2. multi-agent system
3. multi-agent system without critic/falsification loop

Use the same blind fault scenarios and evaluation criteria where possible.

The evaluation should report actual measured values.

Never fabricate metrics.

---

# 22. ARCHITECTURE

Target repository:

```text
NEXUS/
│
├── AGENTS.md
├── .env
├── .env.example
├── .gitignore
├── docker-compose.yml
├── README.md
│
├── backend/
│   ├── AGENTS.md
│   └── app/
│
├── production/
│   ├── AGENTS.md
│   └── ...
│
├── orchestrator/
│   ├── AGENTS.md
│   └── ...
│
├── agents/
│   ├── AGENTS.md
│   └── ...
│
├── mcp/
│   ├── AGENTS.md
│   └── ...
│
├── guardrails/
│   ├── AGENTS.md
│   └── ...
│
├── fault_injection/
│   ├── AGENTS.md
│   └── ...
│
├── evaluation/
│   ├── AGENTS.md
│   └── ...
│
├── dashboard/
│   ├── AGENTS.md
│   └── ...
│
├── tests/
│
└── docs/
    ├── ARCHITECTURE.md
    ├── API_CONTRACT.md
    ├── EVENT_SCHEMA.md
    ├── EVALUATION.md
    └── PROJECT_STATE.md
```

---

# 23. DEPENDENCY ISOLATION

The verified `backend/` and `production/` environments must not be broken by ADK, LiteLLM, MCP SDK, or agent dependencies.

Prefer:

```text
backend/requirements.txt
production/requirements.txt
mcp/requirements.txt
orchestrator/requirements.txt
agents/requirements.txt
```

and separate Docker build contexts/environments where appropriate.

Do not casually install new packages into a shared environment.

Before dependency upgrades:

1. inspect current versions
2. isolate the experiment
3. run compatibility tests
4. verify Phase 1/2
5. only then update pinned dependencies

---

# 24. IMPLEMENTATION ORDER

Follow this order unless a documented architectural reason requires a change.

### Phase 1 — Foundation
Completed.

### Phase 2 — Observability
Completed and verified.

### Phase 2.5 — ADK/Groq Spike
Mandatory before substantial agent implementation.

- ADK Python
- GPT-OSS 120B via Groq
- LiteLLM bridge
- one agent
- one tool
- actual tool calling
- dependency isolation
- regression test

### Phase 3 — MCP

Build real MCP diagnostic servers/tools around the production simulation.

### Phase 4 — Independent Diagnostic Agents

Implement:

- Metrics Agent
- Logs & Traces Agent
- Change Analysis Agent
- Database Agent

Each should have:

- clear responsibility
- structured output
- MCP access
- tests
- local documentation

### Phase 5 — A2A + Orchestration

Implement:

- Incident Manager
- genuine A2A communication
- Evidence Agent
- Root-Cause Critic
- bounded re-evaluation loop
- persistent incident state

### Phase 6 — Event Bridge + Backend

Connect ADK events/A2A/MCP activity to the backend event store and API.

### Phase 7 — Dashboard

Build the live investigation visualization.

### Phase 8 — Guardrails + Recovery

Implement bounded recovery, approval, validation, sandbox execution, and kill switch.

### Phase 9 — Fault Injection

Implement controlled scenarios and ground truth.

### Phase 10 — Evaluation

Implement baselines, ablation, metrics, and reports.

### Phase 11 — Integration + Demo

Run the complete end-to-end scenario.

---

# 25. TESTING REQUIREMENTS

At minimum:

```text
unit tests
integration tests
A2A tests
MCP tests
LLM/tool-calling smoke test
event-stream tests
fault-injection tests
recovery safety tests
dashboard/backend integration tests
full end-to-end test
```

Before moving between major phases:

```text
pytest
docker compose config
docker build
docker compose up
health checks
relevant scenario test
```

Do not claim Docker works unless Docker has actually been tested.

---

# 26. FAILURE HANDLING

If something breaks:

1. Stop expanding scope.
2. Identify the first failing layer.
3. Preserve the last verified state.
4. Fix the smallest relevant component.
5. Re-run the smallest relevant test.
6. Re-run regression tests.
7. Update PROJECT_STATE.md.

Never hide failures by:

- changing expected results
- weakening tests
- removing failing functionality
- silently changing the LLM
- silently changing providers
- marking incomplete features complete

---

# 27. CONTEXT-AWARE Codex WORKFLOW

For every task:

```text
1. Read root AGENTS.md
2. Read docs/PROJECT_STATE.md
3. Identify the component
4. Read that component's AGENTS.md
5. Read only relevant contracts
6. Inspect only necessary source
7. Implement one coherent unit
8. Test it
9. Update PROJECT_STATE.md
10. Continue
```

When a task spans components, read the local instructions for those components only.

Do not preload unrelated folders.

When a task is complete, leave enough durable information in the filesystem that another Codex session can continue without relying on conversation history.

---

# 28. GIT DISCIPLINE

Git is the historical record.

Use meaningful commits at stable milestones.

Do not commit:

```text
.env
API keys
credentials
tokens
private certificates
temporary secrets
```

Before a commit:

```text
git status
tests
secret check
diff review
```

Do not make commits claiming work by Mukund or Vanshika unless they actually made that contribution.

---

# 29. FINAL DEMO

The final demo should be reproducible:

```text
Start NEXUS
    ↓
Start simulated production
    ↓
Inject controlled failure
    ↓
Incident appears
    ↓
Incident Manager starts investigation
    ↓
Specialist agents activate
    ↓
A2A requests/responses appear
    ↓
Agents use MCP tools
    ↓
Evidence appears
    ↓
Evidence Agent forms hypothesis
    ↓
Root-Cause Critic challenges it
    ↓
Missing evidence requested
    ↓
Agents investigate again
    ↓
Hypothesis updated
    ↓
Supported diagnosis OR abstention
    ↓
Recovery plan generated
    ↓
Safety validation
    ↓
Human approval
    ↓
Controlled recovery
    ↓
Verification
    ↓
Incident resolved
```

The dashboard should make each major transition visible.

---

# 30. DEFINITION OF DONE

NEXUS is complete only when all of the following are true:

- [ ] simulated production environment works
- [ ] controlled fault injection works
- [ ] metrics work
- [ ] logs work
- [ ] traces work
- [ ] DB diagnostics work
- [ ] change/deployment history works
- [ ] MCP tools are real
- [ ] diagnostic agents are real
- [ ] A2A communication is real and demonstrable
- [ ] Incident Manager is implemented
- [ ] Evidence Agent is implemented
- [ ] Root-Cause Critic is implemented
- [ ] re-evaluation loop is bounded and functional
- [ ] diagnosis can abstain
- [ ] incident state persists
- [ ] event stream is complete enough for auditing
- [ ] dashboard shows live investigation activity
- [ ] Groq/GPT-OSS runtime integration works
- [ ] LLM usage/quota visibility works where provider data permits
- [ ] token/call budgets exist
- [ ] recovery is bounded
- [ ] human approval exists
- [ ] kill switch exists
- [ ] fault-injection benchmark exists
- [ ] baseline exists
- [ ] critic ablation exists
- [ ] quantitative evaluation exists
- [ ] tests pass
- [ ] Docker end-to-end works
- [ ] no secrets are committed
- [ ] documentation reflects actual implementation
- [ ] PROJECT_STATE.md is current

---

# 31. FIRST ACTION FOR A NEW Codex SESSION

Do NOT immediately code.

First:

1. Read this root `AGENTS.md`.
2. Read `docs/PROJECT_STATE.md`.
3. Identify the current phase.
4. Read the local `AGENTS.md` only for the component being worked on.
5. Inspect only the relevant files.
6. Check the last verified tests.
7. Continue from the existing state.

If the next phase is not obvious, inspect PROJECT_STATE.md rather than scanning the entire repository.

---

# 32. CURRENT PRIORITY

The immediate priority after Phase 2 is:

> **Run and verify the ADK + GPT-OSS 120B via Groq compatibility spike before implementing substantial MCP/agent/orchestration code.**

Do not proceed past the spike until:

- actual model invocation works
- actual tool calling works
- dependency isolation is acceptable
- Phase 1/2 regression tests still pass

After that, proceed to MCP, then real independent agents/A2A, then orchestration, persistence/event streaming, dashboard, guardrails, fault injection, and evaluation.

**Preserve working code. Keep context small. Use real protocols. Test everything. Never fabricate functionality or contributions.**
