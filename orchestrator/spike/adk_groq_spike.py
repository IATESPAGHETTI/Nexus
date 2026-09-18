"""Phase 2.5 mandatory spike (root CLAUDE.md section 9.1).

Proves, with a real (not mocked) call, that:
  1. an ADK LlmAgent can be built with GPT-OSS 120B via Groq (through LiteLLM)
  2. the model actually responds
  3. the model actually performs a real tool call
  4. the tool result actually reaches the model and shapes its final answer

Run with the isolated spike venv (see orchestrator/CLAUDE.md), never the shared
backend/production venv:

    .venv-orchestrator/Scripts/python orchestrator/spike/adk_groq_spike.py

Never prints GROQ_API_KEY. Exits non-zero on any failed check.
"""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

import litellm
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import InMemoryRunner
from google.genai import types

REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(REPO_ROOT / ".env")

# Groq's GPT-OSS models return a `reasoning_content` field on assistant
# messages that Groq's own chat-completions schema then rejects when that
# message is replayed back to it in a later turn (tool-calling multi-turn
# loop). Known LiteLLM/Groq compatibility issue (BerriAI/litellm#8136,
# #14163, #16129) — drop_params strips unsupported fields instead of
# failing the request.
litellm.drop_params = True

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

# The value the tool returns is arbitrary and only known to the tool, so a
# correct final answer proves the tool result actually reached the model
# rather than the model guessing.
SECRET_VALUE = 8271


def get_incident_severity_code() -> dict:
    """Trivial diagnostic-shaped tool: returns a fixed, non-guessable code."""
    return {"severity_code": SECRET_VALUE}


async def run_spike() -> bool:
    if not GROQ_API_KEY:
        print("FAIL: GROQ_API_KEY not set in .env")
        return False

    agent = Agent(
        name="spike_agent",
        # include_reasoning=False: Groq-specific param for GPT-OSS models that
        # suppresses the `reasoning`/`reasoning_content` field on responses.
        # Without it, ADK/LiteLLM echoes that field back on the next turn and
        # Groq's own schema then rejects it (see comment above on drop_params).
        model=LiteLlm(model=f"groq/{GROQ_MODEL}", include_reasoning=False),
        instruction=(
            "You must call the get_incident_severity_code tool to look up the "
            "incident severity code, then state the exact numeric code in your "
            "final answer. Do not guess the number."
        ),
        tools=[get_incident_severity_code],
    )

    runner = InMemoryRunner(agent=agent, app_name="nexus_adk_spike")
    session = await runner.session_service.create_session(
        app_name="nexus_adk_spike", user_id="spike_user"
    )

    user_message = types.Content(
        role="user",
        parts=[types.Part(text="What is the current incident severity code?")],
    )

    tool_called = False
    tool_result_seen = False
    final_text = ""

    async for event in runner.run_async(
        user_id="spike_user",
        session_id=session.id,
        new_message=user_message,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "function_call", None):
                    if part.function_call.name == "get_incident_severity_code":
                        tool_called = True
                if getattr(part, "function_response", None):
                    response = part.function_response.response
                    if response and response.get("severity_code") == SECRET_VALUE:
                        tool_result_seen = True
                if getattr(part, "text", None):
                    final_text += part.text

    model_responded = bool(final_text.strip())
    tool_result_in_answer = str(SECRET_VALUE) in final_text

    print(f"model identifier requested: groq/{GROQ_MODEL}")
    print(f"model responded: {model_responded}")
    print(f"tool actually called: {tool_called}")
    print(f"tool result observed in event stream: {tool_result_seen}")
    print(f"tool result present in final answer: {tool_result_in_answer}")
    print(f"final answer (truncated): {final_text[:200]!r}")

    return model_responded and tool_called and tool_result_seen and tool_result_in_answer


def main() -> int:
    ok = asyncio.run(run_spike())
    print("SPIKE RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
