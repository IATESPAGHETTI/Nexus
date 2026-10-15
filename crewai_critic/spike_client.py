"""Calls the spike server from the ADK side with the SAME helper the orchestrator uses (RemoteA2aAgent).
Run with .venv-orchestrator. Usage: spike_client.py [port]"""
import asyncio, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "orchestrator"))
sys.path.insert(0, str(ROOT / "agents" / "common"))
import ports
port = int(sys.argv[1]) if len(sys.argv) > 1 else 8116
ports.A2A_PORTS["crewai_spike"] = port
from remote_call import call_remote_agent

r = asyncio.run(call_remote_agent("crewai_spike", "CrewAI critic spike", json.dumps({"hypothesis": {"statement": "DB slow"}, "evidence_pool": [{"evidence_id": "ev-1"}]})))
print(json.dumps(r, indent=1))
