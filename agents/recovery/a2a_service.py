"""Recovery Agent as an independent A2A service (Phase 8).

    .venv-agents/Scripts/python agents/recovery/a2a_service.py

Serves the real A2A protocol on its own port (agents/common/ports.py) -- a
separate OS process, same pattern as every other agent service. Agent Card at
http://127.0.0.1:<port>/.well-known/agent-card.json.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

import uvicorn  # noqa: E402
from a2a_server import build_a2a_app  # noqa: E402
from agent import recovery_agent  # noqa: E402
from ports import A2A_HOST, A2A_PORTS  # noqa: E402

PORT = A2A_PORTS[recovery_agent.agent_name]

app = build_a2a_app(recovery_agent, host=A2A_HOST, port=PORT)

if __name__ == "__main__":
    uvicorn.run(app, host=A2A_HOST, port=PORT)
