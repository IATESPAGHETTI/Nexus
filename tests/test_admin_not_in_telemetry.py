"""NEXUS's own /admin control-plane calls must not show up in the metrics, logs
or traces the diagnostic agents read -- otherwise they "diagnose" the test
harness ("POST /admin/fault/inject") instead of the real symptom."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "production"))

from fastapi.testclient import TestClient  # noqa: E402

import state  # noqa: E402
from service import app  # noqa: E402

client = TestClient(app)


def setup_function(_fn):
    state.clear_all()


def test_admin_calls_leave_no_trace_in_metrics_logs_or_traces():
    client.post("/admin/fault/inject", json={"fault_type": "db_slowdown"})
    client.get("/admin/state")
    client.post("/admin/fault/clear")

    assert not any("/admin" in endpoint for endpoint in client.get("/metrics").json()["by_endpoint"])
    assert not any(e["path"].startswith("/admin") for e in client.get("/logs?limit=200").json()["entries"])
    assert not any(t["path"].startswith("/admin") for t in client.get("/traces?limit=200").json()["traces"])


def test_customer_traffic_is_still_recorded():
    client.get("/orders")
    assert any(e["path"] == "/orders" for e in client.get("/logs?limit=200").json()["entries"])
