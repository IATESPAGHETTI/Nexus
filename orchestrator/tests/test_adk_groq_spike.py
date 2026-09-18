"""Automated regression form of the Phase 2.5 spike (orchestrator/spike/adk_groq_spike.py).

Makes a REAL call to Groq — requires GROQ_API_KEY in the repo-root .env. Run with
the isolated orchestrator venv, not the shared backend/production venv:

    .venv-orchestrator/Scripts/python -m pytest orchestrator/tests -q
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "spike"))

from adk_groq_spike import run_spike  # noqa: E402


def test_adk_groq_gpt_oss_120b_tool_calling():
    assert asyncio.run(run_spike()) is True
