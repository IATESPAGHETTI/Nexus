"""Incident store durability tests (root CLAUDE.md section 15: incident state
must persist).

A backend "restart" is simulated by closing the SQLite connection and letting
the next call reopen the same file -- the exact thing that used to wipe every
incident when the store was a plain in-memory dict. Pure TestClient/SQLite, no
network.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app import incident_store  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture
def file_db(tmp_path, monkeypatch):
    """Points the store at a throwaway database FILE for one test, then hands
    the shared in-memory connection back to the rest of the suite."""
    incident_store.close()
    monkeypatch.setenv("NEXUS_DB_PATH", str(tmp_path / "nexus-test.db"))
    yield tmp_path / "nexus-test.db"
    incident_store.close()  # env is still the temp file here; drop that connection


def _restart():
    incident_store.close()


def test_incident_state_survives_a_restart(file_db):
    incident = incident_store.create_incident("checkout latency spike")
    incident_id = incident["incident_id"]
    incident_store.update_incident(
        incident_id,
        {"status": "DIAGNOSED", "hypotheses": [{"hypothesis_id": "H1"}], "token_usage": {"total": {"llm_calls": 7}}},
    )

    _restart()

    reloaded = incident_store.get_incident(incident_id)
    assert reloaded is not None
    assert reloaded["description"] == "checkout latency spike"
    assert reloaded["status"] == "DIAGNOSED"
    assert reloaded["hypotheses"] == [{"hypothesis_id": "H1"}]
    assert reloaded["token_usage"]["total"]["llm_calls"] == 7
    assert file_db.exists()


def test_events_survive_a_restart_in_order_with_a_matching_timeline(file_db):
    incident_id = incident_store.create_incident("x")["incident_id"]
    for event_type in ("INCIDENT_CREATED", "AGENT_STARTED", "AGENT_COMPLETED"):
        incident_store.append_event(incident_id, event_type, "incident_manager", None, None, {"n": event_type})

    _restart()

    events = incident_store.list_events(incident_id)
    assert [e["event_type"] for e in events] == ["INCIDENT_CREATED", "AGENT_STARTED", "AGENT_COMPLETED"]
    assert events[1]["payload"] == {"n": "AGENT_STARTED"}
    timeline = incident_store.get_incident(incident_id)["timeline"]
    assert [t["event_id"] for t in timeline] == [e["event_id"] for e in events]


def test_event_ids_keep_increasing_across_a_restart(file_db):
    incident_id = incident_store.create_incident("x")["incident_id"]
    first = incident_store.append_event(incident_id, "A", "s", None, None, None)

    _restart()

    second = incident_store.append_event(incident_id, "B", "s", None, None, None)
    assert int(second["event_id"].split("-")[1]) > int(first["event_id"].split("-")[1])
    assert [e["event_type"] for e in incident_store.list_events(incident_id)] == ["A", "B"]


def test_unknown_incident_is_still_none_after_a_restart(file_db):
    incident_store.create_incident("x")
    _restart()
    assert incident_store.get_incident("INC-nope") is None
    assert incident_store.update_incident("INC-nope", {"status": "X"}) is None
    assert incident_store.append_event("INC-nope", "A", "s", None, None, None) is None
    assert incident_store.list_events("INC-nope") is None


def test_clear_refuses_to_wipe_a_file_backed_database(file_db):
    incident_id = incident_store.create_incident("precious")["incident_id"]
    with pytest.raises(RuntimeError):
        incident_store.clear()
    assert incident_store.get_incident(incident_id) is not None


def test_http_api_serves_incidents_that_were_created_before_a_restart(file_db):
    client = TestClient(app)
    incident_id = client.post("/incidents", json={"description": "orders endpoint failing"}).json()["incident_id"]
    client.post(f"/incidents/{incident_id}/events", json={"event_type": "INCIDENT_CREATED", "source": "incident_manager"})
    client.post(f"/incidents/{incident_id}/state", json={"token_usage": {"total": {"llm_calls": 3}}})

    _restart()

    body = client.get(f"/incidents/{incident_id}").json()
    assert body["description"] == "orders endpoint failing"
    assert body["token_usage"]["total"]["llm_calls"] == 3
    assert [e["event_type"] for e in client.get(f"/incidents/{incident_id}/events").json()["events"]] == ["INCIDENT_CREATED"]
