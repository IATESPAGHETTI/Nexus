"""Counts the model usage an agent actually incurred, from its own ADK event stream.

Every non-partial ADK event that carries `usage_metadata` is one real model
response (ADK's LiteLlm wrapper fills it from the provider's own `usage`
block). Summing them gives the real number of model calls and tokens one
agent task used -- measured, never estimated. If the provider returns no usage
block, nothing is counted here and `as_dict()["llm_calls"]` stays 0; the
orchestrator (`orchestrator/budget.py`) treats that as "unmeasured" and falls
back to a lower bound of 1 call per task instead of pretending it was free.
"""

from __future__ import annotations


def _count(value) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else 0


class UsageTally:
    def __init__(self) -> None:
        self.llm_calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0

    def add_event(self, event) -> None:
        meta = getattr(event, "usage_metadata", None)
        if meta is None or getattr(event, "partial", False):
            return
        prompt = _count(getattr(meta, "prompt_token_count", 0))
        completion = _count(getattr(meta, "candidates_token_count", 0))
        total = _count(getattr(meta, "total_token_count", 0)) or prompt + completion
        self.llm_calls += 1
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += total

    def as_dict(self) -> dict:
        return {
            "llm_calls": self.llm_calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }
