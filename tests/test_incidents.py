"""Backend incident state + event store tests (Phase 6).

Pure TestClient tests (no live server, no network) -- same pattern as
tests/test_health.py. Covers backend/app/incident_store.py and the
/incidents* endpoints in backend/app/main.py that
orchestrator/event_bridge.py relies on for real HTTP calls during a live
investigation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app import incident_store  # noqa: E402
from app.main import app  # noqa: E402

client = TestClient(app)


def setup_function(_fn):
    incident_store.clear()


def test_create_incident_returns_full_initial_state():
    response = client.post("/incidents", json={"description": "checkout latency spike"})
    assert response.status_code == 200
    body = response.json()
    assert body["incident_id"].startswith("INC-")
    assert body["status"] == "INVESTIGATING"
    assert body["description"] == "checkout latency spike"
    assert body["hypotheses"] == []
    assert body["timeline"] == []


def test_get_unknown_incident_is_404():
    response = client.get("/incidents/INC-doesnotexist")
    assert response.status_code == 404


def test_event_lifecycle_updates_timeline_and_is_listable():
    incident_id = client.post("/incidents", json={"description": "db slowdown"}).json()["incident_id"]

    event_resp = client.post(
        f"/incidents/{incident_id}/events",
        json={
            "event_type": "HYPOTHESIS_CREATED",
            "source": "evidence_agent",
            "target": None,
            "status": None,
            "payload": {"hypothesis_id": "H1"},
        },
    )
    assert event_resp.status_code == 200
    event = event_resp.json()
    assert event["event_id"]
    assert event["incident_id"] == incident_id
    assert event["event_type"] == "HYPOTHESIS_CREATED"
    assert event["payload"] == {"hypothesis_id": "H1"}

    events = client.get(f"/incidents/{incident_id}/events").json()["events"]
    assert len(events) == 1
    assert events[0]["event_id"] == event["event_id"]

    incident = client.get(f"/incidents/{incident_id}").json()
    assert len(incident["timeline"]) == 1
    assert incident["timeline"][0]["event_type"] == "HYPOTHESIS_CREATED"


def test_event_on_unknown_incident_is_404():
    response = client.post(
        "/incidents/INC-doesnotexist/events",
        json={"event_type": "AGENT_STARTED", "source": "metrics_agent"},
    )
    assert response.status_code == 404


def test_state_update_merges_fields_without_clobbering_others():
    incident_id = client.post("/incidents", json={"description": "config error"}).json()["incident_id"]

    client.post(f"/incidents/{incident_id}/state", json={"hypotheses": [{"hypothesis_id": "H1"}]})
    incident = client.post(f"/incidents/{incident_id}/state", json={"status": "DIAGNOSED"}).json()

    assert incident["status"] == "DIAGNOSED"
    assert incident["hypotheses"] == [{"hypothesis_id": "H1"}]
    assert incident["description"] == "config error"  # untouched field preserved


def test_state_update_on_unknown_incident_is_404():
    response = client.post("/incidents/INC-doesnotexist/state", json={"status": "DIAGNOSED"})
    assert response.status_code == 404
