"""Checkout: GET /products and POST /orders, and how each fault breaks them for real."""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "production"))

from fastapi.testclient import TestClient  # noqa: E402

import db  # noqa: E402
import state  # noqa: E402
from service import app  # noqa: E402

client = TestClient(app)


def setup_function(_fn):
    state.clear_all()


def teardown_function(_fn):
    """Checkout tests insert orders into the shared in-memory DB; remove them (seed rows are ids 1-10)
    so other tests that expect the seeded data are unaffected."""
    state.clear_all()
    conn = db.get_connection()
    conn.execute("DELETE FROM orders WHERE id > 10")
    conn.commit()


def _count():
    return len(client.get("/orders").json()["orders"])


def test_catalog_is_a_static_list_with_positive_prices():
    products = client.get("/products").json()["products"]
    assert len(products) >= 6
    assert len({p["id"] for p in products}) == len(products)
    assert all(p["price"] > 0 and p["name"] for p in products)


def test_checkout_creates_an_order_priced_by_the_server():
    before = _count()
    body = {"customer": "tester", "items": [{"product_id": 1, "quantity": 2}, {"product_id": 5, "quantity": 1}], "price": 0.01}
    response = client.post("/orders", json=body)
    assert response.status_code == 201
    order = response.json()["order"]
    assert order["amount"] == round(59.00 * 2 + 12.75, 2)  # client-supplied price ignored
    assert order["customer"] == "tester" and order["status"] == "completed"
    assert _count() == before + 1
    assert client.get(f"/orders/{order['id']}").json()["amount"] == order["amount"]


def test_checkout_rejects_bad_input_and_creates_nothing():
    before = _count()
    bad = [
        {"customer": "x", "items": []},
        {"customer": "", "items": [{"product_id": 1, "quantity": 1}]},
        {"customer": "x", "items": [{"product_id": 1, "quantity": 0}]},
        {"customer": "x", "items": [{"product_id": 1, "quantity": 11}]},
        {"customer": "x" * 41, "items": [{"product_id": 1, "quantity": 1}]},
        {"customer": "x", "items": [{"product_id": 1, "quantity": 1}] * 11},
    ]
    for body in bad:
        assert client.post("/orders", json=body).status_code == 422, body
    assert client.post("/orders", json={"customer": "x", "items": [{"product_id": 999, "quantity": 1}]}).status_code == 400
    assert _count() == before


def test_config_error_breaks_checkout_and_creates_no_order():
    before = _count_with_faults_off()
    client.post("/admin/fault/inject", json={"fault_type": "config_error"})
    response = client.post("/orders", json={"customer": "x", "items": [{"product_id": 1, "quantity": 1}]})
    assert response.status_code == 500 and "ConfigError" in response.text
    client.post("/admin/fault/clear")
    assert _count() == before


def _count_with_faults_off():
    state.clear_all()
    return _count()


def test_slow_database_makes_checkout_really_slow():
    client.post("/admin/fault/inject", json={"fault_type": "db_slowdown"})
    start = time.perf_counter()
    response = client.post("/orders", json={"customer": "x", "items": [{"product_id": 1, "quantity": 1}]})
    elapsed = time.perf_counter() - start
    assert response.status_code == 201 and elapsed >= 0.2
    # and the Database Agent's data shows it: the INSERT is in the recorded query summary
    recent = client.get("/db/diagnostics").json()["recent_queries"]
    assert any(q["sql"].startswith("INSERT") and q["duration_ms"] >= 200 for q in recent)


def test_the_shop_page_uses_the_catalog_and_checkout_but_never_admin():
    html = client.get("/shop").text
    assert "/products" in html and "/orders" in html and "/admin" not in html
