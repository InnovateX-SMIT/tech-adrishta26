from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_get_system_info_endpoint():
    response = client.get("/api/system/info")
    assert response.status_code == 200

    data = response.json()
    assert data["project"] == "RESQ"
    assert data["mode"] == "development"
    assert data["mesh_enabled"] is False
    assert data["encryption_enabled"] is False
    assert data["phase"] == 1


def test_system_info_does_not_falsely_claim_security_enabled():
    response = client.get("/api/system/info")
    assert response.status_code == 200
    data = response.json()
    # Explicit boundary check: Phase 1 must never claim encryption or mesh are active
    assert data["encryption_enabled"] is False
    assert data["mesh_enabled"] is False
