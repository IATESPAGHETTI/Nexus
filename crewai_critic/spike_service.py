"""SPIKE (not the final Critic): a CrewAI agent served over real A2A.

    CRITIC_STUB=1 .venv-crewai/Scripts/python crewai_critic/spike_service.py   # 0 tokens: tests the protocol only
    .venv-crewai/Scripts/python crewai_critic/spike_service.py                 # real CrewAI + DeepSeek call

CrewAI 1.15.28 can build an AgentCard (A2AServerConfig) but ships no server, so the
HTTP/JSON-RPC server is a2a-sdk (the protocol library) and the reasoning is a CrewAI Agent.
"""
import asyncio
import json
import os
from pathlib import Path

import uvicorn
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, Part, TaskState, TextPart
from dotenv import load_dotenv

HOST, PORT = "127.0.0.1", int(os.environ.get("SPIKE_PORT", "8116"))
STUB = os.environ.get("CRITIC_STUB") == "1"

for parent in Path(__file__).resolve().parents:  # a git worktree has no .env of its own
    if (parent / ".env").exists():
        load_dotenv(parent / ".env")
        break


def run_crewai(text: str) -> str:
    from crewai import LLM, Agent

    agent = Agent(
        role="Root-cause critic",
        goal="Challenge a hypothesis using only the evidence given.",
        backstory="You are sceptical and cite evidence ids.",
        llm=LLM(model="deepseek/deepseek-chat", api_key=os.environ["DEEPSEEK_API_KEY"], max_tokens=120, temperature=0),
        allow_delegation=False,
        verbose=False,
    )
    result = agent.kickoff(
        'Reply with ONE line of JSON only: {"verdict": "SUPPORTED" or "INSUFFICIENT_EVIDENCE", "rationale": "<10 words"}. Input: '
        + text[:500]
    )
    return result.raw


class CriticExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.submit()
        await updater.start_work()
        text = context.get_user_input() or ""
        if STUB:
            answer = json.dumps({"verdict": "INSUFFICIENT_EVIDENCE", "rationale": "stub", "echo_chars": len(text), "framework": "stub"})
        else:
            answer = await asyncio.to_thread(run_crewai, text)
        await updater.complete(updater.new_agent_message([Part(root=TextPart(text=answer))]))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await TaskUpdater(event_queue, context.task_id, context.context_id).update_status(TaskState.canceled)


card = AgentCard(
    name="root_cause_critic_crewai_spike",
    description="CrewAI-backed critic (spike).",
    url=f"http://{HOST}:{PORT}/",
    version="0.0.1",
    default_input_modes=["text"],
    default_output_modes=["text"],
    capabilities=AgentCapabilities(streaming=False),
    skills=[AgentSkill(id="critique", name="critique", description="Challenge a hypothesis", tags=["critic"])],
)
app = A2AStarletteApplication(
    agent_card=card,
    http_handler=DefaultRequestHandler(agent_executor=CriticExecutor(), task_store=InMemoryTaskStore()),
).build()

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
