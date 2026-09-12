from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_get_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "RESQ backend"
    assert data["phase"] == "phase-1"


def test_cors_headers_development():
    response = client.get(
        "/api/health",
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
