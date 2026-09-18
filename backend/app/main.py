from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

from . import incident_store

app = FastAPI(title="nexus-backend")


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "nexus-backend"}


class IncidentCreate(BaseModel):
    description: str


class EventCreate(BaseModel):
    event_type: str
    source: str
    target: str | None = None
    status: str | None = None
    payload: dict[str, Any] | None = None


class IncidentStateUpdate(BaseModel):
    """Partial incident-state merge (root CLAUDE.md section 15 fields). Accepts
    any subset of known fields plus forward-compatible extras -- validation of
    field *meaning* is the orchestrator's job, not this persistence layer's
    (backend/CLAUDE.md "no business logic here")."""

    model_config = ConfigDict(extra="allow")


@app.post("/incidents")
def create_incident(body: IncidentCreate) -> dict:
    return incident_store.create_incident(body.description)


@app.get("/incidents/{incident_id}")
def get_incident(incident_id: str) -> dict:
    incident = incident_store.get_incident(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return incident


@app.post("/incidents/{incident_id}/state")
def update_incident_state(incident_id: str, body: IncidentStateUpdate) -> dict:
    incident = incident_store.update_incident(incident_id, body.model_dump(exclude_unset=True))
    if incident is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return incident


@app.post("/incidents/{incident_id}/events")
def create_event(incident_id: str, body: EventCreate) -> dict:
    event = incident_store.append_event(
        incident_id, body.event_type, body.source, body.target, body.status, body.payload
    )
    if event is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return event


@app.get("/incidents/{incident_id}/events")
def get_events(incident_id: str) -> dict:
    events = incident_store.list_events(incident_id)
    if events is None:
        raise HTTPException(status_code=404, detail="incident not found")
    return {"events": events}
