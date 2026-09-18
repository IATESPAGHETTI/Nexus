import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "production"))

from fastapi.testclient import TestClient  # noqa: E402

from service import app  # noqa: E402

client = TestClient(app)


def test_metrics_reflects_traffic():
    client.get("/health")
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.json()
    assert body["request_count"] >= 1
    assert "GET /health" in body["by_endpoint"]


def test_logs_recorded():
    client.get("/health")
    response = client.get("/logs?limit=5")
    assert response.status_code == 200
    entries = response.json()["entries"]
    assert len(entries) >= 1
    assert entries[0]["path"] in {"/health", "/logs"}


def test_trace_roundtrip():
    resp = client.get("/health")
    trace_id = resp.headers["X-Trace-Id"]
    detail = client.get(f"/traces/{trace_id}")
    assert detail.status_code == 200
    assert detail.json()["trace_id"] == trace_id


def test_trace_not_found():
    response = client.get("/traces/doesnotexist")
    assert response.status_code == 404


def test_changes_history():
    response = client.get("/changes")
    assert response.status_code == 200
    body = response.json()["changes"]
    assert len(body) >= 1
    assert body == sorted(body, key=lambda c: c["deployed_at"], reverse=True)


def test_orders_and_db_diagnostics():
    orders = client.get("/orders")
    assert orders.status_code == 200
    order_list = orders.json()["orders"]
    assert len(order_list) == 10

    single = client.get(f"/orders/{order_list[0]['id']}")
    assert single.status_code == 200

    missing = client.get("/orders/9999")
    assert missing.status_code == 404

    diag = client.get("/db/diagnostics")
    assert diag.status_code == 200
    diag_body = diag.json()
    assert diag_body["table_row_counts"]["orders"] == 10
    assert diag_body["query_summary"]["total_queries"] >= 1
