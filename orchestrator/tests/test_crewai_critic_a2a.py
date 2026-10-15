"""ADK client (a2a-sdk 1.x) -> CrewAI Critic (a2a-sdk 0.3.x) over real A2A, stub mode (0 tokens).
Starts the CrewAI service as its own process from .venv-crewai; skipped when that venv is absent."""
import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
VENV_PY = ROOT / ".venv-crewai" / "Scripts" / "python.exe"
if not VENV_PY.exists():  # worktrees share the main checkout's venvs
    for parent in ROOT.parents:
        if (parent / ".venv-crewai" / "Scripts" / "python.exe").exists():
            VENV_PY = parent / ".venv-crewai" / "Scripts" / "python.exe"
            break
pytestmark = pytest.mark.skipif(not VENV_PY.exists(), reason=".venv-crewai not created")

sys.path.insert(0, str(ROOT / "orchestrator"))
sys.path.insert(0, str(ROOT / "agents" / "common"))
PORT = 8126


@pytest.fixture(scope="module")
def service():
    env = {**os.environ, "CRITIC_STUB": "1", "CRITIC_PORT": str(PORT)}
    proc = subprocess.Popen([str(VENV_PY), str(ROOT / "crewai_critic" / "a2a_service.py")], env=env,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                socket.create_connection(("127.0.0.1", PORT), timeout=0.5).close()
                break
            except OSError:
                time.sleep(0.5)
        else:
            pytest.fail("CrewAI critic service did not start")
        yield proc
    finally:
        proc.kill()


def test_adk_client_gets_a_crewai_critique_over_a2a(service, monkeypatch):
    import ports
    monkeypatch.setitem(ports.A2A_PORTS, "root_cause_critic", PORT)
    from remote_call import call_remote_agent
    msg = json.dumps({"hypothesis": {"hypothesis_id": "H1", "statement": "x"}, "evidence_pool": []})
    out = asyncio.run(call_remote_agent("root_cause_critic", "crewai critic", msg))
    assert out["task_id"] and out["context_id"]  # a real A2A task happened
    assert out["response"]["framework"] == "crewai"
    assert out["response"]["hypothesis_id"] == "H1"
    assert out["response"]["verdict"] == "INSUFFICIENT_EVIDENCE"
