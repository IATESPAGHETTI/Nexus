"""POST /admin/reset returns the shop to a clean slate so one incident's leftovers can't pollute the next."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "production"))

from fastapi.testclient import TestClient  # noqa: E402

import changes  # noqa: E402
import state  # noqa: E402
from service import app  # noqa: E402

client = TestClient(app)


def test_reset_clears_faults_history_and_extra_orders():
    state.inject("config_error")
    client.get("/orders")  # a recorded 500
    changes.append("deployment", "9.9.9", "leftover from an earlier incident")
    client.post("/orders", json={"items": [{"product_id": 1, "quantity": 1}]})

    assert client.post("/admin/reset").status_code == 200

    assert not any(state.snapshot()[k] for k in ("config_error", "db_slowdown", "bad_deployment"))
    assert len(changes.recent(50)) == 3
    assert client.get("/logs").json()["entries"] == []  # read first: each call is itself logged
    assert client.get("/metrics").json()["request_count"] == 1  # only the /logs call above
    assert len(client.get("/orders").json()["orders"]) == 10
