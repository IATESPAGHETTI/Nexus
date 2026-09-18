from fastapi.testclient import TestClient

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "production"))

from app.main import app as backend_app  # noqa: E402
from service import app as production_app  # noqa: E402


def test_backend_health():
    client = TestClient(backend_app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "nexus-backend"}


def test_production_health():
    client = TestClient(production_app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "nexus-production"}
