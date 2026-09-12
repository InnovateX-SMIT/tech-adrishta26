from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_get_system_info_endpoint():
    response = client.get("/api/system/info")
    assert response.status_code == 200

    data = response.json()
    assert data["project"] == "RESQ"
    assert data["mode"] == "development"
    assert data["mesh_enabled"] is True       # Phase 4: mesh is active
    assert data["encryption_enabled"] is False
    assert data["phase"] == 4                 # Phase 4


def test_system_info_does_not_falsely_claim_security_enabled():
    response = client.get("/api/system/info")
    assert response.status_code == 200
    data = response.json()
    # Phase 4 boundary check: encryption is still off, only mesh is enabled
    assert data["encryption_enabled"] is False
    assert data["mesh_enabled"] is True       # Phase 4 activates mesh
