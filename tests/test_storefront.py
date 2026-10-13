"""The /shop storefront page: served, self-contained, and its requests are ordinary customer traffic."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "production"))

from fastapi.testclient import TestClient  # noqa: E402

import state  # noqa: E402
from service import app  # noqa: E402

client = TestClient(app)


def setup_function(_fn):
    state.clear_all()


def test_shop_page_is_served_as_html_and_labelled_simulated():
    response = client.get("/shop")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "SIMULATED" in response.text and "/orders" in response.text


def test_shop_only_calls_the_existing_order_endpoints():
    html = client.get("/shop").text
    assert "/admin" not in html  # the page can never reach the control plane


def test_dockerfile_copies_every_file_the_service_needs():
    dockerfile = (Path(__file__).resolve().parents[1] / "production" / "Dockerfile").read_text(encoding="utf-8")
    for needed in ("service.py", "db.py", "observability.py", "changes.py", "state.py", "catalog.py", "storefront.html"):
        assert needed in dockerfile, needed
