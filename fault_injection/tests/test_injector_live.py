"""Real end-to-end test of fault_injection/injector.py against a live
production/ service -- nothing mocked, same philosophy as mcp/tests.

Requires production/ running and reachable at PRODUCTION_BASE_URL:
    docker compose up -d production
    or: cd production && ../.venv/Scripts/python -m uvicorn service:app --port 8001

Run:
    python -m pytest fault_injection/tests/test_injector_live.py -q
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest  # noqa: E402

import injector  # noqa: E402


@pytest.fixture(autouse=True)
def _clear_faults():
    injector.clear()
    yield
    injector.clear()


def test_inject_and_clear_bad_deployment_round_trip():
    state = injector.inject("FI-bad-deployment")
    assert state["bad_deployment"] is True

    cleared = injector.clear()
    assert cleared["bad_deployment"] is False


def test_current_state_reflects_a_real_injection():
    injector.inject("FI-db-slowdown")
    state = injector.current_state()
    assert state["db_slowdown"] is True
