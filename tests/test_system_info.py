from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_get_system_info_endpoint():
    response = client.get("/api/system/info")
    assert response.status_code == 200

    data = response.json()
    assert data["project"] == "RESQ"
    assert data["mode"] == "development"
    assert data["mesh_enabled"] is True
    assert data["encryption_enabled"] is True     # Phase 8: all phases active
    assert data["phase"] == 8


def test_system_info_reflects_phase6_active():
    response = client.get("/api/system/info")
    assert response.status_code == 200
    data = response.json()
    assert data["encryption_enabled"] is True
    assert data["mesh_enabled"] is True
    assert data["phase"] == 8

