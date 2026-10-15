"""attach_report and emit_monitor with the backend mocked out (deterministic, no network, no tokens)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import event_bridge  # noqa: E402
import investigation  # noqa: E402

INCIDENT = {
    "incident_id": "INC-9", "description": "d", "status": "DIAGNOSED",
    "decision": {"outcome": "DIAGNOSED", "reason": "ok", "loops_used": 1},
    "hypotheses": [{"hypothesis_id": "H1", "statement": "s", "confidence": 0.7, "status": "SUPPORTED",
                    "supporting_evidence_ids": [], "created_at": "t"}],
    "critic_results": [], "agent_findings": {},
}


def test_attach_report_saves_json_and_markdown(monkeypatch):
    saved = {}
    monkeypatch.setattr(event_bridge, "get_incident", lambda i: INCIDENT)
    monkeypatch.setattr(event_bridge, "update_state", lambda i, **f: saved.update(f))
    investigation.attach_report("INC-9")
    assert saved["report"]["root_cause"] == "s"
    assert saved["report"]["markdown"].startswith("# Incident report INC-9")


def test_attach_report_never_raises_when_saving_fails(monkeypatch):
    def boom(i, **f):
        raise RuntimeError("backend rejected state")
    monkeypatch.setattr(event_bridge, "get_incident", lambda i: INCIDENT)
    monkeypatch.setattr(event_bridge, "update_state", boom)
    assert investigation.attach_report("INC-9") == INCIDENT  # outcome unchanged


def test_emit_monitor_posts_event_and_ignores_garbage(monkeypatch):
    events = []
    monkeypatch.setattr(event_bridge, "emit_event", lambda *a, **k: events.append((a, k)))
    event_bridge.emit_monitor("INC-9", "metrics_agent", {"errors": 1, "records": []})
    event_bridge.emit_monitor("INC-9", "metrics_agent", None)
    event_bridge.emit_monitor("INC-9", "metrics_agent", "not a dict")
    assert len(events) == 1 and events[0][0][1] == "AGENT_MONITOR" and events[0][1]["status"] == "errors"
