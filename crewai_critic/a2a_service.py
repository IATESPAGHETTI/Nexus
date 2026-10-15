"""Root-Cause Critic implemented with CrewAI, served over real A2A (course requirements 6 and 7).

    .venv-crewai/Scripts/python crewai_critic/a2a_service.py

Same contract as the ADK Critic (`agents/critic/critic_core.py`: same instruction, same verdict enum,
same `build_critique` + Pydantic validation) and the SAME A2A address (`root_cause_critic`, port 8106),
so the orchestrator cannot tell which framework answered, except for the `framework` field on the
critique. CrewAI ships no A2A server, so the protocol server is a2a-sdk (0.3.x) and the reasoning is a
CrewAI `Agent`. Set CRITIC_STUB=1 for a deterministic, zero-token mode used by protocol tests.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_TRACING_ENABLED", "false")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # CrewAI prints emoji; Windows consoles are cp1252
    except Exception:  # noqa: BLE001
        pass

REPO_ROOT = Path(__file__).resolve().parents[1]
for p in (REPO_ROOT, REPO_ROOT / "agents" / "critic", REPO_ROOT / "agents" / "common"):
    sys.path.insert(0, str(p))

import uvicorn  # noqa: E402
from a2a.server.agent_execution import AgentExecutor, RequestContext  # noqa: E402
from a2a.server.apps import A2AStarletteApplication  # noqa: E402
from a2a.server.events import EventQueue  # noqa: E402
from a2a.server.request_handlers import DefaultRequestHandler  # noqa: E402
from a2a.server.tasks import InMemoryTaskStore, TaskUpdater  # noqa: E402
from a2a.types import AgentCapabilities, AgentCard, AgentSkill, Part, TaskState, TextPart  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

from callbacks import AgentMonitor  # noqa: E402
from critic_core import AGENT_NAME, DESCRIPTION, INSTRUCTION, build_critique  # noqa: E402
from json_extract import extract_json  # noqa: E402
from prompt_variants import apply_variant  # noqa: E402
from nexus_trace import TraceContextMiddleware  # noqa: E402
from board_io import parse_board_message, run_on_board  # noqa: E402
from nexus_guard import redact_text  # noqa: E402

for _parent in Path(__file__).resolve().parents:  # a git worktree has no .env of its own
    if (_parent / ".env").exists():
        load_dotenv(_parent / ".env")
        break

HOST = os.environ.get("NEXUS_BIND_HOST", "127.0.0.1")
ADVERTISE = os.environ.get("NEXUS_ADVERTISE_HOST", HOST)
PORT = int(os.environ.get("CRITIC_PORT", "8106"))
STUB = os.environ.get("CRITIC_STUB") == "1"
MODEL = os.environ.get("NEXUS_CREWAI_MODEL", "deepseek/deepseek-chat")


def run_crewai(payload_text: str, monitor: AgentMonitor) -> tuple[str, dict]:
    """One CrewAI agent run. Returns (raw model text, usage dict in NEXUS budget shape)."""
    from crewai import LLM, Agent

    agent = Agent(
        role="NEXUS Root-Cause Critic",
        goal="Independently challenge the hypothesis under review using only the evidence given.",
        backstory=apply_variant(INSTRUCTION, AGENT_NAME),
        llm=LLM(model=MODEL, api_key=os.environ["DEEPSEEK_API_KEY"], temperature=0, max_tokens=1500),
        allow_delegation=False,
        verbose=False,
    )
    monitor.before_model(None, SimpleNamespace(contents=[payload_text]))
    try:
        result = agent.kickoff(payload_text)
    except Exception as exc:  # noqa: BLE001
        monitor.on_model_error(None, None, exc)
        raise
    metrics = getattr(result, "usage_metrics", None) or getattr(result, "token_usage", None)
    usage = {
        "llm_calls": int(getattr(metrics, "successful_requests", 0) or 0),
        "prompt_tokens": int(getattr(metrics, "prompt_tokens", 0) or 0),
        "completion_tokens": int(getattr(metrics, "completion_tokens", 0) or 0),
        "total_tokens": int(getattr(metrics, "total_tokens", 0) or 0),
    }
    monitor.after_model(
        None,
        SimpleNamespace(
            usage_metadata=SimpleNamespace(
                prompt_token_count=usage["prompt_tokens"], candidates_token_count=usage["completion_tokens"]
            ),
            content=None,
            error_code=None,
        ),
    )
    return result.raw, usage


def critique_for(question: str) -> dict:
    """Pure function used by the A2A executor and by tests."""
    monitor = AgentMonitor(AGENT_NAME)
    if os.environ.get("NEXUS_GUARDRAILS", "1") != "0":
        question, guard_flags = redact_text(question)  # same layer as the ADK agents' tool-output guard
        if guard_flags:
            monitor._add("input_redacted", flags=guard_flags)
    try:
        payload = json.loads(question)
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    hypothesis = payload.get("hypothesis") or {}
    evidence_pool = payload.get("evidence_pool") or []

    if STUB:
        raw_text = json.dumps({"verdict": "INSUFFICIENT_EVIDENCE", "rationale": "stub mode (no model call)"})
        usage = {"llm_calls": 0, "prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
    else:
        raw_text, usage = run_crewai(question, monitor)
    monitor.after_agent(None)

    critique = build_critique(hypothesis, evidence_pool, extract_json(raw_text))
    critique["framework"] = "crewai"
    critique["usage"] = usage
    critique["monitoring"] = monitor.summary()
    return critique


class CrewAICriticExecutor(AgentExecutor):
    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        updater = TaskUpdater(event_queue, context.task_id, context.context_id)
        await updater.submit()
        await updater.start_work()
        try:
            text = context.get_user_input() or ""
            board = parse_board_message(text)
            if board:  # blackboard topology: read the board, write the critique back, reply with an ack
                critique = await run_on_board(lambda q: asyncio.to_thread(critique_for, q), board, AGENT_NAME)
            else:
                critique = await asyncio.to_thread(critique_for, text)
            await updater.complete(updater.new_agent_message([Part(root=TextPart(text=json.dumps(critique)))]))
        except Exception as exc:  # noqa: BLE001 -- surface as a failed A2A task, never a hung one
            await updater.failed(updater.new_agent_message([Part(root=TextPart(text=f"{type(exc).__name__}: {str(exc)[:200]}"))]))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        await TaskUpdater(event_queue, context.task_id, context.context_id).update_status(TaskState.canceled)


def build_app():
    card = AgentCard(
        name=AGENT_NAME,
        description=DESCRIPTION + " (CrewAI implementation)",
        url=f"http://{ADVERTISE}:{PORT}/",
        version="1.0.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[AgentSkill(id="critique_hypothesis", name="critique_hypothesis",
                           description="Challenge a hypothesis against an evidence pool", tags=["critic", "crewai"])],
    )
    handler = DefaultRequestHandler(agent_executor=CrewAICriticExecutor(), task_store=InMemoryTaskStore())
    built = A2AStarletteApplication(agent_card=card, http_handler=handler).build()
    built.add_middleware(TraceContextMiddleware)
    return built


app = build_app()

if __name__ == "__main__":
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
