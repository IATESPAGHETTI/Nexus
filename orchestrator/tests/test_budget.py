"""Unit tests for orchestrator/budget.py (root CLAUDE.md section 8 spending limits).

Pure Python, no network, no model calls:
    .venv-orchestrator/Scripts/python -m pytest orchestrator/tests/test_budget.py -q
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from budget import (  # noqa: E402
    DEFAULT_MAX_LLM_CALLS,
    DEFAULT_MAX_TOKENS_PER_AGENT,
    DEFAULT_MAX_TOTAL_TOKENS,
    IncidentBudget,
)


def _usage(calls, prompt, completion):
    return {"llm_calls": calls, "prompt_tokens": prompt, "completion_tokens": completion, "total_tokens": prompt + completion}


def test_record_adds_up_usage_across_agents():
    budget = IncidentBudget()
    budget.record("metrics_agent", _usage(2, 1000, 200))
    budget.record("database_agent", _usage(3, 500, 100))
    budget.record("metrics_agent", _usage(1, 50, 10))

    snap = budget.snapshot()
    assert snap["total"] == {"llm_calls": 6, "prompt_tokens": 1550, "completion_tokens": 310, "total_tokens": 1860}
    assert snap["by_agent"]["metrics_agent"]["total_tokens"] == 1260
    assert snap["by_agent"]["metrics_agent"]["tasks"] == 2
    assert snap["unmeasured_tasks"] == 0
    assert snap["budget_exceeded"] is None


def test_call_limit_reached_stops_further_calls():
    budget = IncidentBudget(max_llm_calls=5)
    budget.record("a", _usage(4, 10, 10))
    assert budget.exceeded() is None
    budget.record("b", _usage(1, 10, 10))
    assert "MAX_LLM_CALLS_PER_INCIDENT" in budget.exceeded()


def test_total_token_limit_reached_stops_further_calls():
    budget = IncidentBudget(max_total_tokens=1000)
    budget.record("a", _usage(1, 600, 100))
    assert budget.exceeded() is None
    budget.record("b", _usage(1, 250, 50))
    assert "MAX_TOTAL_TOKENS_PER_INCIDENT" in budget.exceeded()


def test_per_agent_token_limit_names_the_agent():
    budget = IncidentBudget(max_tokens_per_agent=500)
    budget.record("quiet_agent", _usage(1, 100, 10))
    budget.record("chatty_agent", _usage(1, 450, 100))
    reason = budget.exceeded()
    assert "chatty_agent" in reason and "MAX_TOKENS_PER_AGENT" in reason


@pytest.mark.parametrize("missing", [None, {}, _usage(0, 0, 0), "garbage"])
def test_task_without_usage_counts_as_one_unmeasured_call(missing):
    budget = IncidentBudget()
    budget.record("metrics_agent", missing)
    snap = budget.snapshot()
    assert snap["total"]["llm_calls"] == 1
    assert snap["total"]["total_tokens"] == 0
    assert snap["unmeasured_tasks"] == 1


def test_invalid_numbers_are_ignored_not_trusted():
    budget = IncidentBudget()
    budget.record("a", {"llm_calls": 2, "prompt_tokens": -50, "completion_tokens": True, "total_tokens": "lots"})
    snap = budget.snapshot()
    assert snap["total"]["llm_calls"] == 2
    assert snap["total"]["prompt_tokens"] == 0
    assert snap["total"]["completion_tokens"] == 0
    assert snap["total"]["total_tokens"] == 0


def test_from_env_reads_limits(monkeypatch):
    monkeypatch.setenv("MAX_LLM_CALLS_PER_INCIDENT", "7")
    monkeypatch.setenv("MAX_TOTAL_TOKENS_PER_INCIDENT", "12345")
    monkeypatch.setenv("MAX_TOKENS_PER_AGENT", "999")
    limits = IncidentBudget.from_env().snapshot()["limits"]
    assert limits == {"max_llm_calls": 7, "max_total_tokens": 12345, "max_tokens_per_agent": 999}


@pytest.mark.parametrize("bad", ["", "   ", "abc", "0", "-5", "1.5"])
def test_from_env_falls_back_to_defaults_on_bad_values(monkeypatch, bad):
    for name in ("MAX_LLM_CALLS_PER_INCIDENT", "MAX_TOTAL_TOKENS_PER_INCIDENT", "MAX_TOKENS_PER_AGENT"):
        monkeypatch.setenv(name, bad)
    limits = IncidentBudget.from_env().snapshot()["limits"]
    assert limits == {
        "max_llm_calls": DEFAULT_MAX_LLM_CALLS,
        "max_total_tokens": DEFAULT_MAX_TOTAL_TOKENS,
        "max_tokens_per_agent": DEFAULT_MAX_TOKENS_PER_AGENT,
    }


def test_from_env_uses_defaults_when_unset(monkeypatch):
    for name in ("MAX_LLM_CALLS_PER_INCIDENT", "MAX_TOTAL_TOKENS_PER_INCIDENT", "MAX_TOKENS_PER_AGENT"):
        monkeypatch.delenv(name, raising=False)
    assert IncidentBudget.from_env().snapshot()["limits"]["max_llm_calls"] == DEFAULT_MAX_LLM_CALLS
