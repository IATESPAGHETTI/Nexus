"""Shared runner for NEXUS reasoning agents (Phase 6: Evidence Agent, Root-Cause
Critic) that reason over structured input already produced elsewhere in the
system, rather than calling MCP tools themselves.

Unlike `DiagnosticAgent` (agents/common/diagnostic_agent.py), this class gives
the ADK Agent NO tools: the JSON payload it receives in the user message *is*
the evidence it may use. This keeps the evidence-first guarantee alive across
Phase 6 -- these agents can only ever reason over evidence that some diagnostic
agent already gathered through a real MCP tool call; they cannot invent a new
observation the way an untooled chatbot could.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import litellm
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.genai import types

from usage_tally import UsageTally

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
load_dotenv(REPO_ROOT / ".env")

from runtime_config import litellm_model_name, resolve_runtime_config  # noqa: E402

# Same real Groq free-tier TPM constraint as agents/common/diagnostic_agent.py.
litellm.num_retries = 5

_FENCED_JSON_RE = re.compile(r"```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str):
    """Best-effort structured extraction from a model's free-form reply.

    Tries a fenced ```json block first, then the raw stripped text, then the
    largest top-level {...}/[...] span in the text. Returns None (never raises)
    if nothing in the text parses as JSON -- callers must treat that as "the
    model gave no usable structured output" and fail safe, not guess.
    """
    if not text:
        return None
    candidates: list[str] = []
    fenced = _FENCED_JSON_RE.search(text)
    if fenced:
        candidates.append(fenced.group(1))
    stripped = text.strip()
    candidates.append(stripped)
    first = min((i for i in (stripped.find("{"), stripped.find("[")) if i != -1), default=-1)
    if first != -1:
        last = max(stripped.rfind("}"), stripped.rfind("]"))
        if last > first:
            candidates.append(stripped[first : last + 1])
    for candidate in candidates:
        try:
            return json.loads(candidate)
        except (json.JSONDecodeError, TypeError):
            continue
    return None


class ReasoningAgent:
    """An ADK LlmAgent with no tools: reasons purely over the JSON it is given
    as input and is instructed to reply with structured JSON output. Exposes
    the same `build_adk_agent()` / `default_question` / async `investigate()`
    shape `agents/common/a2a_server.py` already expects from a DiagnosticAgent,
    so it is reused unmodified to serve these agents over real A2A too.
    """

    def __init__(self, agent_name: str, instruction: str, default_question: str, description: str = ""):
        self.agent_name = agent_name
        self.instruction = instruction
        self.default_question = default_question
        self.description = description

    def build_adk_agent(self) -> Agent:
        provider, _ = resolve_runtime_config()
        model_kwargs = {"include_reasoning": False} if provider == "groq" else {}
        return Agent(
            name=self.agent_name,
            description=self.description,
            model=LiteLlm(model=litellm_model_name(), **model_kwargs),
            instruction=self.instruction,
            tools=[],
        )

    async def investigate(self, question: str) -> dict:
        agent = self.build_adk_agent()
        runner = InMemoryRunner(agent=agent, app_name=f"nexus_{self.agent_name}")
        session = await runner.session_service.create_session(
            app_name=f"nexus_{self.agent_name}", user_id="nexus"
        )
        user_message = types.Content(role="user", parts=[types.Part(text=question)])

        final_text = ""
        usage = UsageTally()
        async for event in runner.run_async(
            user_id="nexus", session_id=session.id, new_message=user_message
        ):
            usage.add_event(event)
            if not (event.content and event.content.parts):
                continue
            for part in event.content.parts:
                text = getattr(part, "text", None)
                if text:
                    final_text += text

        return {"raw_text": final_text, "parsed": extract_json(final_text), "usage": usage.as_dict()}
