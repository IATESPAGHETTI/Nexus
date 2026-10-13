"""Per-investigation LLM token metering (root CLAUDE.md section 8).

Counts only what the provider reported: ADK surfaces LiteLLM's `usage` as
`event.usage_metadata` on each model-response event. If a provider reports
nothing, the meter stays at zero calls and callers show "Unavailable from
provider" -- nothing is estimated.
"""

from __future__ import annotations


class UsageMeter:
    def __init__(self) -> None:
        self.calls = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.total_tokens = 0

    def observe(self, event) -> None:
        usage = getattr(event, "usage_metadata", None)
        if usage is None or getattr(event, "partial", False):
            return
        prompt = getattr(usage, "prompt_token_count", None) or 0
        completion = getattr(usage, "candidates_token_count", None) or 0
        total = getattr(usage, "total_token_count", None) or (prompt + completion)
        if not total:
            return
        self.calls += 1
        self.prompt_tokens += prompt
        self.completion_tokens += completion
        self.total_tokens += total

    def as_dict(self) -> dict:
        return {
            "llm_calls": self.calls,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
        }
