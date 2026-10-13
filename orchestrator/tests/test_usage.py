"""Token usage is provider-reported only: summed per agent/incident, never estimated."""

import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "orchestrator"))
sys.path.insert(0, str(ROOT / "agents" / "common"))

import usage_tracker  # noqa: E402
from llm_usage import UsageMeter  # noqa: E402


def _event(prompt, completion, total=None, partial=False, usage=True):
    meta = SimpleNamespace(prompt_token_count=prompt, candidates_token_count=completion, total_token_count=total)
    return SimpleNamespace(usage_metadata=meta if usage else None, partial=partial)


def test_meter_sums_only_reported_usage():
    m = UsageMeter()
    m.observe(_event(100, 20, 120))
    m.observe(_event(50, 10))  # total derived from the parts the provider reported
    m.observe(_event(0, 0, 0))  # nothing reported -> not counted
    m.observe(_event(1, 1, 2, partial=True))  # streaming partial -> not counted
    m.observe(_event(1, 1, usage=False))  # no usage metadata -> not counted
    assert m.as_dict() == {"llm_calls": 2, "prompt_tokens": 150, "completion_tokens": 30, "total_tokens": 180}


def test_take_usage_strips_key():
    result = {"x": 1, "llm_usage": {"total_tokens": 5}}
    assert usage_tracker.take_usage(result) == {"total_tokens": 5}
    assert "llm_usage" not in result
    assert usage_tracker.take_usage(None) is None


def test_record_usage_accumulates_and_skips_empty(monkeypatch):
    pushed = []
    monkeypatch.setattr(usage_tracker.event_bridge, "update_state", lambda iid, **f: pushed.append((iid, f)))
    usage_tracker._by_incident.clear()
    usage_tracker.record_usage("INC-1", "metrics_agent", {"llm_calls": 2, "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15})
    usage_tracker.record_usage("INC-1", "metrics_agent", {"llm_calls": 1, "prompt_tokens": 4, "completion_tokens": 1, "total_tokens": 5})
    usage_tracker.record_usage("INC-1", "evidence_agent", None)
    usage_tracker.record_usage("INC-1", "evidence_agent", {"total_tokens": 0})
    assert len(pushed) == 2
    usage = pushed[-1][1]["token_usage"]
    assert usage["total_tokens"] == 20 and usage["llm_calls"] == 3
    assert usage["by_agent"] == {"metrics_agent": {"llm_calls": 3, "prompt_tokens": 14, "completion_tokens": 6, "total_tokens": 20}}
