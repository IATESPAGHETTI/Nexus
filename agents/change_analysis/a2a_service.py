"""Change Analysis Agent as an independent A2A service (Phase 5).

    .venv-agents/Scripts/python agents/change_analysis/a2a_service.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common"))

import uvicorn  # noqa: E402
from a2a_server import build_a2a_app  # noqa: E402
from agent import change_analysis_agent  # noqa: E402
from ports import A2A_HOST, A2A_PORTS  # noqa: E402

PORT = A2A_PORTS[change_analysis_agent.agent_name]

app = build_a2a_app(change_analysis_agent, host=A2A_HOST, port=PORT)

if __name__ == "__main__":
    uvicorn.run(app, host=A2A_HOST, port=PORT)
