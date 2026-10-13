"""A 5xx log entry carries the app's own error message, so diagnosis is possible from logs."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "production"))

from fastapi.testclient import TestClient  # noqa: E402

import state  # noqa: E402
from service import app  # noqa: E402

client = TestClient(app)


def setup_function(_fn):
    state.clear_all()


def teardown_function(_fn):
    state.clear_all()


def _errors():
    return [e for e in client.get("/logs", params={"limit": 20}).json()["entries"] if e["level"] == "ERROR"]


def test_config_error_message_is_in_the_log():
    state.inject("config_error")
    assert client.get("/orders").status_code == 500
    assert any("ConfigError" in e.get("error", "") for e in _errors())


def test_healthy_and_client_errors_have_no_error_field():
    client.get("/orders")
    client.get("/orders/99999")  # 404
    newest = client.get("/logs", params={"limit": 2}).json()["entries"]  # the two requests just made
    assert all("error" not in e for e in newest)
