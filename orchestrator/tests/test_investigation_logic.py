"""Deterministic orchestration-logic tests for the Phase 6 bounded
re-evaluation loop (orchestrator/investigation.py).

Real A2A/MCP/Groq nondeterminism makes the contradiction/abstention paths hard
to hit reliably against a live LLM without wasting Groq's free-tier quota on
retries. These tests exercise `run_investigation`'s actual control-flow code
with test doubles ONLY at its two network boundaries:

  - `investigation.investigate_incident` (the Phase 5 real-A2A diagnostic
    dispatch -- already covered by real network calls in
    orchestrator/tests/test_incident_manager.py and this phase's own
    test_investigation_e2e.py)
  - `investigation.call_remote_agent` (the Phase 6 real-A2A call to the
    Evidence Agent / Root-Cause Critic -- likewise covered for real in
    test_investigation_e2e.py)
  - `event_bridge.*` (real HTTP calls to backend/ -- covered for real in
    test_investigation_e2e.py)

This is standard unit-level testing of the orchestration layer itself, not a
claim that A2A/MCP are being exercised here -- see test_investigation_e2e.py
for the real, live, protocol-level end-to-end proof.

Run with the isolated orchestrator venv:
    .venv-orchestrator/Scripts/python -m pytest orchestrator/tests/test_investigation_logic.py -q
"""

import sys
from pathlib import Path

import pytest
import pytest_asyncio

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import event_bridge  # noqa: E402
import investigation  # noqa: E402

FINDING_A = {
    "finding_id": "find-a",
    "agent": "metrics_agent",
    "evidence": [{"evidence_id": "ev-a1", "tool": "get_metrics", "arguments": {}, "result": {"ok": True}}],
    "confidence": 0.9,
}
FINDING_B = {
    "finding_id": "find-b",
    "agent": "database_agent",
    "evidence": [{"evidence_id": "ev-b1", "tool": "get_database_stats", "arguments": {}, "result": {"ok": True}}],
    "confidence": 0.8,
}

HYPOTHESIS_1 = {
    "hypothesis_id": "H1",
    "statement": "Database is the bottleneck",
    "supporting_evidence_ids": ["ev-b1"],
    "contradicting_evidence_ids": [],
    "confidence": 0.9,
    "missing_evidence": [],
    "requested_next_investigation": None,
    "status": "PROPOSED",
}
HYPOTHESIS_2 = {
    "hypothesis_id": "H2",
    "statement": "Metrics endpoint is slow",
    "supporting_evidence_ids": ["ev-a1"],
    "contradicting_evidence_ids": [],
    "confidence": 0.5,
    "missing_evidence": [],
    "requested_next_investigation": None,
    "status": "PROPOSED",
}


class _FakeBackend:
    """In-memory stand-in for the real backend/ HTTP service, satisfying the
    exact same call shapes orchestrator/event_bridge.py's real functions have."""

    def __init__(self):
        self.incident = None
        self.events = []

    def create_incident(self, description):
        self.incident = {"incident_id": "INC-fake", "description": description, "status": "INVESTIGATING"}
        return "INC-fake"

    def emit_event(self, incident_id, event_type, source, target=None, status=None, payload=None):
        event = {"event_type": event_type, "source": source, "target": target, "status": status, "payload": payload or {}}
        self.events.append(event)
        return event

    def update_state(self, incident_id, **fields):
        self.incident.update(fields)
        return dict(self.incident)

    def get_incident(self, incident_id):
        return dict(self.incident)


@pytest_asyncio.fixture
def fake_backend(monkeypatch):
    backend = _FakeBackend()
    monkeypatch.setattr(event_bridge, "create_incident", backend.create_incident)
    monkeypatch.setattr(event_bridge, "emit_event", backend.emit_event)
    monkeypatch.setattr(event_bridge, "update_state", backend.update_state)
    monkeypatch.setattr(event_bridge, "get_incident", backend.get_incident)
    return backend


def _fake_dispatch(findings):
    async def _dispatch(incident_description, agent_names=None):
        names = agent_names or list(findings)
        return {
            "incident_description": incident_description,
            "findings": {n: findings[n] for n in names},
            "a2a": {n: {"task_id": f"t-{n}", "context_id": f"c-{n}"} for n in names},
            "agents_dispatched": names,
            "agents_responded": names,
        }

    return _dispatch


@pytest.mark.asyncio
async def test_supported_verdict_reaches_diagnosis_on_first_loop(fake_backend, monkeypatch):
    monkeypatch.setattr(investigation, "investigate_incident", _fake_dispatch({"metrics_agent": FINDING_A, "database_agent": FINDING_B}))

    async def fake_call_remote_agent(agent_name, description, message_text):
        if agent_name == investigation.EVIDENCE_AGENT_NAME:
            # investigation.py mutates hypothesis dicts in place -- always hand
            # it fresh copies so tests never leak mutated status between them.
            return {"response": {"hypotheses": [dict(HYPOTHESIS_1), dict(HYPOTHESIS_2)]}, "task_id": "t1", "context_id": "c1"}
        return {"response": {"verdict": "SUPPORTED", "hypothesis_id": "H1", "rationale": "backed by ev-b1"}, "task_id": "t2", "context_id": "c2"}

    monkeypatch.setattr(investigation, "call_remote_agent", fake_call_remote_agent)

    result = await investigation.run_investigation(
        "db slowdown", agent_names=["metrics_agent", "database_agent"], max_loops=3, trigger_recovery=False
    )

    assert result["status"] == "DIAGNOSED"
    assert result["decision"]["outcome"] == "DIAGNOSED"
    assert result["decision"]["loops_used"] == 1
    event_types = [e["event_type"] for e in fake_backend.events]
    assert "DIAGNOSIS_REACHED" in event_types
    assert "ABSTENTION" not in event_types


@pytest.mark.asyncio
async def test_contradicted_then_abstain_within_loop_budget(fake_backend, monkeypatch):
    monkeypatch.setattr(investigation, "investigate_incident", _fake_dispatch({"metrics_agent": FINDING_A, "database_agent": FINDING_B}))

    verdicts = iter(["CONTRADICTED", "ABSTAIN"])

    async def fake_call_remote_agent(agent_name, description, message_text):
        if agent_name == investigation.EVIDENCE_AGENT_NAME:
            return {"response": {"hypotheses": [dict(HYPOTHESIS_1), dict(HYPOTHESIS_2)]}, "task_id": "t1", "context_id": "c1"}
        verdict = next(verdicts)
        return {"response": {"verdict": verdict, "hypothesis_id": "H?", "rationale": f"verdict={verdict}"}, "task_id": "t2", "context_id": "c2"}

    monkeypatch.setattr(investigation, "call_remote_agent", fake_call_remote_agent)

    result = await investigation.run_investigation("ambiguous incident", agent_names=["metrics_agent", "database_agent"], max_loops=3)

    assert result["status"] == "ABSTAINED"
    assert result["decision"]["outcome"] == "ABSTAINED"
    assert result["decision"]["loops_used"] == 2  # H1 contradicted (loop 1), H2 abstained (loop 2)
    event_types = [e["event_type"] for e in fake_backend.events]
    assert "ABSTENTION" in event_types
    assert "DIAGNOSIS_REACHED" not in event_types


@pytest.mark.asyncio
async def test_no_hypotheses_at_all_abstains_immediately(fake_backend, monkeypatch):
    monkeypatch.setattr(investigation, "investigate_incident", _fake_dispatch({"metrics_agent": FINDING_A}))

    async def fake_call_remote_agent(agent_name, description, message_text):
        assert agent_name == investigation.EVIDENCE_AGENT_NAME, "critic should never be called with zero hypotheses"
        return {"response": {"hypotheses": []}, "task_id": "t1", "context_id": "c1"}

    monkeypatch.setattr(investigation, "call_remote_agent", fake_call_remote_agent)

    result = await investigation.run_investigation("no clear evidence", agent_names=["metrics_agent"], max_loops=3)

    assert result["status"] == "ABSTAINED"
    assert result["decision"]["reason"] == "no open hypothesis left to evaluate"
    assert result["decision"]["loops_used"] == 1


@pytest.mark.asyncio
async def test_loop_is_bounded_and_abstains_when_exhausted(fake_backend, monkeypatch):
    monkeypatch.setattr(investigation, "investigate_incident", _fake_dispatch({"metrics_agent": FINDING_A, "database_agent": FINDING_B}))

    call_count = {"critic": 0}

    async def fake_call_remote_agent(agent_name, description, message_text):
        if agent_name == investigation.EVIDENCE_AGENT_NAME:
            return {"response": {"hypotheses": [dict(HYPOTHESIS_1)]}, "task_id": "t1", "context_id": "c1"}
        call_count["critic"] += 1
        # A DIFFERENT request each round, so the stall rule cannot fire and only the cap ends it.
        # Always requests more evidence -- never SUPPORTED/CONTRADICTED/ABSTAIN,
        # so the loop can only ever terminate via the max-loop bound.
        return {"response": {"verdict": "REQUEST_MORE_EVIDENCE", "hypothesis_id": "H1", "requested_evidence": [f"get_trace round {call_count['critic']}"], "rationale": "thin"}, "task_id": "t2", "context_id": "c2"}

    monkeypatch.setattr(investigation, "call_remote_agent", fake_call_remote_agent)

    result = await investigation.run_investigation("perpetually inconclusive incident", agent_names=["metrics_agent", "database_agent"], max_loops=2)

    assert result["status"] == "ABSTAINED"
    assert result["decision"]["loops_used"] == 2
    assert call_count["critic"] == 2  # never exceeds MAX_REEVALUATION_LOOPS
    assert "MAX_REEVALUATION_LOOPS" in result["decision"]["reason"]


@pytest.mark.asyncio
async def test_diagnosed_incident_triggers_recovery_hook(fake_backend, monkeypatch):
    """Phase 8 wiring check: a DIAGNOSED decision must call recovery.run_recovery
    exactly once, with the leading hypothesis and the critique that supported
    it -- and an ABSTAINED decision must never call it at all (see the
    contradicted/abstain and max-loop tests above, which run with the default
    trigger_recovery=True and never touch this monkeypatch, proving recovery
    module is not on their path)."""
    monkeypatch.setattr(investigation, "investigate_incident", _fake_dispatch({"metrics_agent": FINDING_A, "database_agent": FINDING_B}))

    async def fake_call_remote_agent(agent_name, description, message_text):
        if agent_name == investigation.EVIDENCE_AGENT_NAME:
            return {"response": {"hypotheses": [dict(HYPOTHESIS_1)]}, "task_id": "t1", "context_id": "c1"}
        return {"response": {"verdict": "SUPPORTED", "hypothesis_id": "H1", "rationale": "backed by ev-b1"}, "task_id": "t2", "context_id": "c2"}

    monkeypatch.setattr(investigation, "call_remote_agent", fake_call_remote_agent)

    recovery_calls = []

    async def fake_run_recovery(incident_id, hypothesis, critique, evidence_pool=None):
        recovery_calls.append((incident_id, hypothesis["hypothesis_id"], critique["verdict"]))
        return {"outcome": "RESOLVED"}

    monkeypatch.setattr(investigation.recovery, "run_recovery", fake_run_recovery)

    await investigation.run_investigation("db slowdown", agent_names=["metrics_agent", "database_agent"], max_loops=3)

    assert len(recovery_calls) == 1
    assert recovery_calls[0][1] == "H1"
    assert recovery_calls[0][2] == "SUPPORTED"


@pytest.mark.asyncio
async def test_skip_critic_ablation_diagnoses_without_ever_calling_critic(fake_backend, monkeypatch):
    """docs/EVALUATION.md's arm 3 ("multi-agent system without critic/
    falsification loop"): skip_critic=True must reach DIAGNOSED using the
    evidence agent's top hypothesis alone, with ZERO calls to root_cause_critic."""
    monkeypatch.setattr(investigation, "investigate_incident", _fake_dispatch({"metrics_agent": FINDING_A, "database_agent": FINDING_B}))

    async def fake_call_remote_agent(agent_name, description, message_text):
        assert agent_name == investigation.EVIDENCE_AGENT_NAME, "critic must never be called when skip_critic=True"
        return {"response": {"hypotheses": [dict(HYPOTHESIS_1), dict(HYPOTHESIS_2)]}, "task_id": "t1", "context_id": "c1"}

    monkeypatch.setattr(investigation, "call_remote_agent", fake_call_remote_agent)

    result = await investigation.run_investigation(
        "db slowdown", agent_names=["metrics_agent", "database_agent"], skip_critic=True, trigger_recovery=False
    )

    assert result["status"] == "DIAGNOSED"
    assert result["decision"]["outcome"] == "DIAGNOSED"
    assert "ablation" in result["decision"]["reason"]
    assert result["critic_results"][0]["rationale"] == "critic skipped for this run (ablation study)"


@pytest.mark.asyncio
async def test_skip_critic_ablation_abstains_when_no_hypotheses(fake_backend, monkeypatch):
    monkeypatch.setattr(investigation, "investigate_incident", _fake_dispatch({"metrics_agent": FINDING_A}))

    async def fake_call_remote_agent(agent_name, description, message_text):
        return {"response": {"hypotheses": []}, "task_id": "t1", "context_id": "c1"}

    monkeypatch.setattr(investigation, "call_remote_agent", fake_call_remote_agent)

    result = await investigation.run_investigation(
        "no evidence", agent_names=["metrics_agent"], skip_critic=True, trigger_recovery=False
    )

    assert result["status"] == "ABSTAINED"


async def _run_with_critic_replies(fake_backend, monkeypatch, replies, max_loops=3):
    calls = {"critic": 0, "dispatch": 0}
    base_dispatch = _fake_dispatch({"metrics_agent": FINDING_A, "database_agent": FINDING_B})

    async def counting_dispatch(*a, **k):
        calls["dispatch"] += 1
        return await base_dispatch(*a, **k)

    monkeypatch.setattr(investigation, "investigate_incident", counting_dispatch)

    async def fake_call_remote_agent(agent_name, description, message_text):
        if agent_name == investigation.EVIDENCE_AGENT_NAME:
            return {"response": {"hypotheses": [dict(HYPOTHESIS_1)]}, "task_id": "t1", "context_id": "c1"}
        reply = replies[min(calls["critic"], len(replies) - 1)]
        calls["critic"] += 1
        return {"response": {"hypothesis_id": "H1", "rationale": "x", **reply}, "task_id": "t2", "context_id": "c2"}

    monkeypatch.setattr(investigation, "call_remote_agent", fake_call_remote_agent)
    result = await investigation.run_investigation(
        "incident", agent_names=["metrics_agent", "database_agent"], max_loops=max_loops, trigger_recovery=False
    )
    return result, calls


@pytest.mark.asyncio
async def test_loop_stops_when_critic_repeats_the_same_request(fake_backend, monkeypatch):
    same = {"verdict": "INSUFFICIENT_EVIDENCE", "requested_evidence": ["get_trace: child spans"]}
    result, calls = await _run_with_critic_replies(fake_backend, monkeypatch, [same], max_loops=5)
    assert result["status"] == "ABSTAINED"
    assert calls["critic"] == 2  # round 1 asks, round 2 repeats -> stop; not 5
    assert "repeated" in result["decision"]["reason"]


@pytest.mark.asyncio
async def test_loop_stops_when_critic_requests_nothing_obtainable(fake_backend, monkeypatch):
    nothing = {"verdict": "INSUFFICIENT_EVIDENCE", "requested_evidence": [], "unobtainable_evidence": ["stack trace"]}
    result, calls = await _run_with_critic_replies(fake_backend, monkeypatch, [nothing], max_loops=5)
    assert result["status"] == "ABSTAINED"
    assert calls["critic"] == 1 and calls["dispatch"] == 1  # no pointless re-dispatch
    assert "no further obtainable evidence" in result["decision"]["reason"]


@pytest.mark.asyncio
async def test_new_request_then_supported_still_diagnoses(fake_backend, monkeypatch):
    replies = [
        {"verdict": "REQUEST_MORE_EVIDENCE", "requested_evidence": ["get_metrics: error rate"]},
        {"verdict": "SUPPORTED"},
    ]
    result, calls = await _run_with_critic_replies(fake_backend, monkeypatch, replies)
    assert result["status"] == "DIAGNOSED" and calls["critic"] == 2 and calls["dispatch"] == 2
