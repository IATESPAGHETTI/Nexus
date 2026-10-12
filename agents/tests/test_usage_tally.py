"""Fast unit tests for agents/common/usage_tally.py -- pure Python, no network,
no model call. Events are plain stand-ins carrying the same attributes ADK's
Event has (`usage_metadata.*_token_count`, `partial`).

Run with the isolated agents venv:
    .venv-agents/Scripts/python -m pytest agents/tests/test_usage_tally.py -q
"""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

from usage_tally import UsageTally  # noqa: E402


def _event(prompt=None, completion=None, total=None, partial=False, has_usage=True):
    meta = SimpleNamespace(prompt_token_count=prompt, candidates_token_count=completion, total_token_count=total)
    return SimpleNamespace(usage_metadata=meta if has_usage else None, partial=partial)


def test_each_model_response_event_is_one_call_and_tokens_add_up():
    tally = UsageTally()
    tally.add_event(_event(prompt=1000, completion=50, total=1050))
    tally.add_event(_event(prompt=1200, completion=80, total=1280))
    assert tally.as_dict() == {"llm_calls": 2, "prompt_tokens": 2200, "completion_tokens": 130, "total_tokens": 2330}


def test_events_without_usage_are_not_counted():
    tally = UsageTally()
    tally.add_event(_event(has_usage=False))  # e.g. a tool-result event
    assert tally.as_dict()["llm_calls"] == 0


def test_streaming_partials_are_not_double_counted():
    tally = UsageTally()
    tally.add_event(_event(prompt=10, completion=5, total=15, partial=True))
    tally.add_event(_event(prompt=10, completion=5, total=15, partial=False))
    assert tally.as_dict()["llm_calls"] == 1
    assert tally.as_dict()["total_tokens"] == 15


def test_missing_total_falls_back_to_prompt_plus_completion():
    tally = UsageTally()
    tally.add_event(_event(prompt=300, completion=20, total=None))
    assert tally.as_dict()["total_tokens"] == 320


def test_bad_values_never_inflate_the_count():
    tally = UsageTally()
    tally.add_event(_event(prompt=-5, completion=True, total="many"))
    assert tally.as_dict() == {"llm_calls": 1, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
