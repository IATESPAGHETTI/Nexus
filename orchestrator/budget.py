"""Per-incident LLM spending limits (root CLAUDE.md section 8).

`IncidentBudget` adds up the model usage every agent task reports back
(`agents/common/usage_tally.py`, measured from the provider's own `usage`
block) and says when an investigation must stop calling the model. The
orchestrator checks it before each costly step and ABSTAINS -- it never forces
a diagnosis just because the budget ran out.

Limits come from environment variables so nothing is hard-coded:

    MAX_LLM_CALLS_PER_INCIDENT   model calls across all agents   (default 60)
    MAX_TOTAL_TOKENS_PER_INCIDENT  prompt+completion tokens, all agents (default 250000)
    MAX_TOKENS_PER_AGENT         tokens used by any single agent  (default 80000)

The defaults are conservative guesses sized well above a normal 3-round
investigation, NOT measured values -- tune them after a real run. Unset, blank,
non-numeric or non-positive values fall back to the default.

Counting is a lower bound, never an invention: if an agent task reports no
usage (the provider sent none), it is counted as 1 call with unknown tokens and
flagged in `unmeasured_tasks`. Agents that never answered are not counted, and
the Recovery Agent / post-fix verification calls are not counted yet.
"""

from __future__ import annotations

import os

DEFAULT_MAX_LLM_CALLS = 60
DEFAULT_MAX_TOTAL_TOKENS = 250_000
DEFAULT_MAX_TOKENS_PER_AGENT = 80_000

_FIELDS = ("llm_calls", "prompt_tokens", "completion_tokens", "total_tokens")


def _env_limit(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, "").strip())
    except ValueError:
        return default
    return value if value > 0 else default


def _count(value) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


class IncidentBudget:
    def __init__(
        self,
        max_llm_calls: int = DEFAULT_MAX_LLM_CALLS,
        max_total_tokens: int = DEFAULT_MAX_TOTAL_TOKENS,
        max_tokens_per_agent: int = DEFAULT_MAX_TOKENS_PER_AGENT,
    ) -> None:
        self.max_llm_calls = max_llm_calls
        self.max_total_tokens = max_total_tokens
        self.max_tokens_per_agent = max_tokens_per_agent
        self._by_agent: dict[str, dict[str, int]] = {}
        self.unmeasured_tasks = 0

    @classmethod
    def from_env(cls) -> "IncidentBudget":
        return cls(
            max_llm_calls=_env_limit("MAX_LLM_CALLS_PER_INCIDENT", DEFAULT_MAX_LLM_CALLS),
            max_total_tokens=_env_limit("MAX_TOTAL_TOKENS_PER_INCIDENT", DEFAULT_MAX_TOTAL_TOKENS),
            max_tokens_per_agent=_env_limit("MAX_TOKENS_PER_AGENT", DEFAULT_MAX_TOKENS_PER_AGENT),
        )

    def record(self, agent: str, usage: dict | None) -> None:
        """Adds one finished agent task's reported usage. `usage=None` (or a
        report of zero calls) means the task did not report anything, so it is
        counted as a single unmeasured call rather than as free."""
        row = self._by_agent.setdefault(agent, {**{f: 0 for f in _FIELDS}, "tasks": 0})
        row["tasks"] += 1
        counts = {f: _count(usage.get(f)) for f in _FIELDS} if isinstance(usage, dict) else {}
        if not counts.get("llm_calls"):
            self.unmeasured_tasks += 1
            row["llm_calls"] += 1
            return
        for field in _FIELDS:
            row[field] += counts[field]

    def _total(self) -> dict[str, int]:
        return {f: sum(row[f] for row in self._by_agent.values()) for f in _FIELDS}

    def exceeded(self) -> str | None:
        """Why no further model calls may start, or None if there is headroom."""
        total = self._total()
        if total["llm_calls"] >= self.max_llm_calls:
            return f"LLM call budget reached ({total['llm_calls']}/{self.max_llm_calls} calls, MAX_LLM_CALLS_PER_INCIDENT)"
        if total["total_tokens"] >= self.max_total_tokens:
            return f"token budget reached ({total['total_tokens']}/{self.max_total_tokens} tokens, MAX_TOTAL_TOKENS_PER_INCIDENT)"
        for agent, row in self._by_agent.items():
            if row["total_tokens"] >= self.max_tokens_per_agent:
                return f"{agent} token budget reached ({row['total_tokens']}/{self.max_tokens_per_agent} tokens, MAX_TOKENS_PER_AGENT)"
        return None

    def snapshot(self) -> dict:
        """Shape persisted as the incident's `token_usage` (root CLAUDE.md
        section 15) and rendered by the dashboard's usage panel."""
        return {
            "measured_by": "NEXUS, from the model usage each agent reported",
            "total": self._total(),
            "by_agent": {agent: dict(row) for agent, row in self._by_agent.items()},
            "unmeasured_tasks": self.unmeasured_tasks,
            "limits": {
                "max_llm_calls": self.max_llm_calls,
                "max_total_tokens": self.max_total_tokens,
                "max_tokens_per_agent": self.max_tokens_per_agent,
            },
            "budget_exceeded": self.exceeded(),
        }
