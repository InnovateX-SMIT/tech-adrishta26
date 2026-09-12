import pytest
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.registry_service import registry_service, RegistryService
from backend.app.storage.json_store import load_json, save_json

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolate_registry(tmp_path: Path):
    """Ensures each test runs against an isolated temporary registry file."""
    temp_file = tmp_path / "test_registry.json"
    save_json(temp_file, {"version": 1, "members": []})
    original_path = registry_service.registry_path
    registry_service.registry_path = temp_file
    yield temp_file
    registry_service.registry_path = original_path


def test_register_valid_member():
    response = client.post(
        "/api/registry/members",
        json={
            "name": "Aarav Sharma",
            "team": "Rescue Unit A",
            "role": "Field Responder",
        },
    )
    assert response.status_code == 201
    data = response.json()

    assert data["rescue_id"] == "RESQ-001"
    assert data["device_id"] == "DEVICE-001"
    assert data["name"] == "Aarav Sharma"
    assert data["team"] == "Rescue Unit A"
    assert data["role"] == "Field Responder"
    assert data["status"] == "active"
    assert data["signing_public_key"] is None
    assert data["encryption_public_key"] is None
    assert data["created_at"] is not None
    assert data["revoked_at"] is None

    # Strict boundary check: no private key fields in returned payload
    for key in data.keys():
        assert "private" not in key.lower()
        assert "secret" not in key.lower()


def test_register_multiple_members_generates_unique_ids():
    resp1 = client.post(
        "/api/registry/members",
        json={"name": "Member One", "team": "Alpha", "role": "Medic"},
    )
    resp2 = client.post(
        "/api/registry/members",
        json={"name": "Member Two", "team": "Bravo", "role": "Lead"},
    )

    assert resp1.status_code == 201
    assert resp2.status_code == 201

    d1 = resp1.json()
    d2 = resp2.json()

    assert d1["rescue_id"] != d2["rescue_id"]
    assert d1["device_id"] != d2["device_id"]
    assert d1["rescue_id"] == "RESQ-001"
    assert d2["rescue_id"] == "RESQ-002"
    assert d1["device_id"] == "DEVICE-001"
    assert d2["device_id"] == "DEVICE-002"


def test_get_member_by_rescue_id_and_device_id():
    resp = client.post(
        "/api/registry/members",
        json={"name": "Priya Nair", "team": "Unit 7", "role": "Comms"},
    )
    assert resp.status_code == 201
    member = resp.json()

    # Lookup by Rescue ID
    lookup_r = client.get(f"/api/registry/members/{member['rescue_id']}")
    assert lookup_r.status_code == 200
    assert lookup_r.json()["name"] == "Priya Nair"

    # Lookup by Device ID
    lookup_d = client.get(f"/api/registry/devices/{member['device_id']}")
    assert lookup_d.status_code == 200
    assert lookup_d.json()["name"] == "Priya Nair"

    # Unknown Rescue ID returns 404
    assert client.get("/api/registry/members/RESQ-999").status_code == 404

    # Unknown Device ID returns 404
    assert client.get("/api/registry/devices/DEVICE-999").status_code == 404


def test_whitespace_validation_rejects_empty_and_whitespace_only():
    # Empty strings
    assert client.post(
        "/api/registry/members",
        json={"name": "", "team": "Alpha", "role": "Medic"},
    ).status_code == 422

    # Whitespace-only name
    assert client.post(
        "/api/registry/members",
        json={"name": "    ", "team": "Alpha", "role": "Medic"},
    ).status_code == 422

    # Whitespace-only team
    assert client.post(
        "/api/registry/members",
        json={"name": "Aarav", "team": "   ", "role": "Medic"},
    ).status_code == 422

    # Whitespace-only role
    assert client.post(
        "/api/registry/members",
        json={"name": "Aarav", "team": "Alpha", "role": "   "},
    ).status_code == 422

    # Valid string with surrounding whitespace should be trimmed
    trimmed_resp = client.post(
        "/api/registry/members",
        json={"name": "  Aarav Sharma  ", "team": "  Alpha Team  ", "role": "  Lead  "},
    )
    assert trimmed_resp.status_code == 201
    td = trimmed_resp.json()
    assert td["name"] == "Aarav Sharma"
    assert td["team"] == "Alpha Team"
    assert td["role"] == "Lead"


def test_reject_malicious_private_key_payloads():
    malicious_payload = {
        "name": "Attacker",
        "team": "Rogue",
        "role": "Infiltrator",
        "private_key": "super_secret_private_key",
        "signing_private_key": "private_key_material",
    }
    response = client.post("/api/registry/members", json=malicious_payload)
    assert response.status_code == 422


def test_reject_client_supplied_public_keys():
    payload_with_pubkey = {
        "name": "User",
        "team": "Team",
        "role": "Role",
        "signing_public_key": "fake_public_key",
    }
    response = client.post("/api/registry/members", json=payload_with_pubkey)
    assert response.status_code == 422


def test_revocation_lifecycle():
    # 1. Register member
    reg_resp = client.post(
        "/api/registry/members",
        json={"name": "Rohan Mehta", "team": "Bravo", "role": "Scout"},
    )
    assert reg_resp.status_code == 201
    member = reg_resp.json()
    rid = member["rescue_id"]

    # 2. Check active status
    status_resp = client.get(f"/api/registry/members/{rid}/status")
    assert status_resp.status_code == 200
    assert status_resp.json()["is_active"] is True
    assert status_resp.json()["status"] == "active"

    # 3. Revoke member
    revoke_resp = client.post(f"/api/registry/members/{rid}/revoke")
    assert revoke_resp.status_code == 200
    r_data = revoke_resp.json()
    assert r_data["rescue_id"] == rid
    assert r_data["status"] == "revoked"
    assert r_data["is_active"] is False

    # 4. Confirm member status endpoint reports revoked
    status_after = client.get(f"/api/registry/members/{rid}/status")
    assert status_after.status_code == 200
    assert status_after.json()["is_active"] is False
    assert status_after.json()["status"] == "revoked"

    # 5. Confirm service is_member_active returns False
    assert registry_service.is_member_active(rid) is False

    # 6. Confirm revoked member remains in the members list (historical retention)
    list_resp = client.get("/api/registry/members")
    assert list_resp.status_code == 200
    all_members = list_resp.json()
    assert len(all_members) == 1
    assert all_members[0]["rescue_id"] == rid
    assert all_members[0]["status"] == "revoked"
    assert all_members[0]["revoked_at"] is not None

    # 7. Repeated revocation returns 409 Conflict
    repeat_revoke = client.post(f"/api/registry/members/{rid}/revoke")
    assert repeat_revoke.status_code == 409

    # 8. Revoking unknown member returns 404
    assert client.post("/api/registry/members/RESQ-999/revoke").status_code == 404


def test_id_generation_handles_gaps_without_collision(isolate_registry: Path):
    # Pre-populate registry with RESQ-001 and RESQ-003 (simulating gap)
    existing_data = {
        "version": 1,
        "members": [
            {
                "rescue_id": "RESQ-001",
                "name": "First",
                "team": "A",
                "role": "R",
                "device_id": "DEVICE-001",
                "signing_public_key": None,
                "encryption_public_key": None,
                "status": "active",
                "created_at": "2026-09-12T10:00:00Z",
                "revoked_at": None,
            },
            {
                "rescue_id": "RESQ-003",
                "name": "Third",
                "team": "A",
                "role": "R",
                "device_id": "DEVICE-003",
                "signing_public_key": None,
                "encryption_public_key": None,
                "status": "revoked",
                "created_at": "2026-09-12T10:00:00Z",
                "revoked_at": "2026-09-12T10:30:00Z",
            },
        ],
    }
    save_json(isolate_registry, existing_data)

    # Next generated ID must NOT be RESQ-003 or RESQ-002 (since len was 2, 2+1 would be 3 which collided)
    # The max is 3, so next should be RESQ-004
    new_member_resp = client.post(
        "/api/registry/members",
        json={"name": "Fourth", "team": "B", "role": "Medic"},
    )
    assert new_member_resp.status_code == 201
    data = new_member_resp.json()
    assert data["rescue_id"] == "RESQ-004"
    assert data["device_id"] == "DEVICE-004"


def test_persistence_across_service_instances(isolate_registry: Path):
    client.post(
        "/api/registry/members",
        json={"name": "Dev", "team": "Ops", "role": "Lead"},
    )

    # Create a fresh service instance pointing to the same file
    fresh_service = RegistryService(registry_path=isolate_registry)
    members = fresh_service.get_all_members()
    assert len(members) == 1
    assert members[0].name == "Dev"
    assert members[0].rescue_id == "RESQ-001"


def test_security_boundary_no_private_keys_on_disk(isolate_registry: Path):
    client.post(
        "/api/registry/members",
        json={"name": "Alice", "team": "Alpha", "role": "Chief"},
    )

    raw_json = load_json(isolate_registry)
    for m in raw_json.get("members", []):
        for k in m.keys():
            assert "private" not in k.lower()
            assert "secret" not in k.lower()
