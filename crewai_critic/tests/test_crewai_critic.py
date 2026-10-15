"""Run with .venv-crewai. Stub mode: no model call, no tokens."""
import json
import os
import sys
from pathlib import Path

os.environ["CRITIC_STUB"] = "1"
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import a2a_service  # noqa: E402


def test_critique_follows_the_shared_contract():
    out = a2a_service.critique_for(json.dumps({"hypothesis": {"hypothesis_id": "H1"}, "evidence_pool": [{"evidence_id": "e"}]}))
    assert out["framework"] == "crewai"
    assert out["hypothesis_id"] == "H1" and out["verdict"] == "INSUFFICIENT_EVIDENCE"
    assert out["evidence_pool_size"] == 1 and out["critique_id"].startswith("crit-")
    assert out["usage"]["llm_calls"] == 0
    assert out["monitoring"]["agent"] == "root_cause_critic"


def test_garbage_input_still_yields_valid_critique():
    out = a2a_service.critique_for("not json at all")
    assert out["verdict"] == "INSUFFICIENT_EVIDENCE" and out["hypothesis_id"] is None


def test_unknown_verdict_from_model_is_normalised():
    from critic_core import build_critique
    out = build_critique({"hypothesis_id": "H1"}, [], {"verdict": "DEFINITELY", "rationale": "x"})
    assert out["verdict"] == "INSUFFICIENT_EVIDENCE"
