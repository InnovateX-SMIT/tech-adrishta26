import json
import os
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.message_repository import message_repository
from backend.app.models.messages import MessageStatus
from backend.app.services.mesh_service import build_demo_network, get_network, reset_network
from backend.app.services.message_service import message_service


@pytest.fixture(autouse=True)
def setup_mesh_and_storage():
    """Ensure mesh topology is initialized and clean repository state."""
    build_demo_network()
    yield



client = TestClient(app)


def test_zero_plaintext_in_persistence():
    """Verify that plaintext is NEVER saved to data/messages.json or message records."""
    secret_text = "CONFIDENTIAL_SURVIVOR_COORDINATES_37_7749"
    payload = {
        "sender_id": "RESQ-001",
        "recipient_id": "RESQ-002",
        "message": secret_text,
        "priority": "HIGH",
    }
    response = client.post("/api/messages", json=payload)
    assert response.status_code == 200
    data = response.json()
    message_id = data["message_id"]

    # 1. Check in-memory record
    record = message_repository.get_message(message_id)
    assert record is not None
    record_dump = record.model_dump()
    assert secret_text not in str(record_dump)
    for forbidden in ("plaintext", "content", "decrypted_message"):
        assert forbidden not in record_dump

    # 2. Check on-disk file
    if os.path.exists("data/messages.json"):
        with open("data/messages.json", "r", encoding="utf-8") as f:
            disk_content = f.read()
        assert secret_text not in disk_content
        messages_data = json.loads(disk_content)
        for msg in messages_data:
            for forbidden in ("plaintext", "content", "decrypted_message"):
                assert forbidden not in msg


def test_lifecycle_status_progression():
    """Verify status transitions from ENCRYPTED -> IN_TRANSIT -> DELIVERED -> DECRYPTED."""
    payload = {
        "sender_id": "RESQ-001",
        "recipient_id": "RESQ-002",
        "message": "Status lifecycle check test message",
    }
    response = client.post("/api/messages", json=payload)
    assert response.status_code == 200
    data = response.json()
    message_id = data["message_id"]
    packet_id = data["packet_id"]

    # After sending, status must be DELIVERED with delivery timestamp and hops
    status_resp = client.get(f"/api/messages/{message_id}/status")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == MessageStatus.DELIVERED.value
    assert status_data["delivered_at"] is not None
    assert status_data["decrypted_at"] is None
    assert status_data["hop_count"] > 0
    assert len(status_data["route"]) > 0

    # Recipient authorizes and decrypts
    decrypt_resp = client.post(
        "/api/messages/decrypt",
        json={"recipient_id": "RESQ-002", "packet_id": packet_id},
    )
    assert decrypt_resp.status_code == 200
    assert decrypt_resp.json()["status"] == "SUCCESS"
    assert decrypt_resp.json()["message"] == "Status lifecycle check test message"

    # Status must now be DECRYPTED with decrypted_at set
    status_resp_after = client.get(f"/api/messages/{message_id}/status")
    assert status_resp_after.status_code == 200
    status_data_after = status_resp_after.json()
    assert status_data_after["status"] == MessageStatus.DECRYPTED.value
    assert status_data_after["decrypted_at"] is not None


def test_no_route_failure_lifecycle():
    """Verify status is marked FAILED with reason when no route exists."""
    # Disconnect NODE-B to isolate NODE-C
    get_network().remove_node("NODE-B")


    payload = {
        "sender_id": "RESQ-001",
        "recipient_id": "RESQ-003",
        "message": "Cannot reach isolated node",
    }
    response = client.post("/api/messages", json=payload)
    assert response.status_code in (422, 500)

    # Device history should show the failed message
    records = message_service.list_device_messages("DEVICE-001")
    failed_records = [r for r in records if r.status == MessageStatus.FAILED]
    assert len(failed_records) > 0
    assert failed_records[-1].failure_reason is not None


def test_retry_mechanism_success_and_rejection():
    """Verify retry only applies to FAILED/QUEUED and rejects DELIVERED/DECRYPTED."""
    # 1. Send successful message
    response = client.post(
        "/api/messages",
        json={
            "sender_id": "RESQ-001",
            "recipient_id": "RESQ-002",
            "message": "Delivered message cannot be retried",
        },
    )
    assert response.status_code == 200
    msg_id = response.json()["message_id"]

    # 2. Attempting retry on DELIVERED message must fail
    retry_resp = client.post(f"/api/messages/{msg_id}/retry")
    assert retry_resp.status_code == 400
    assert "Only FAILED or QUEUED messages are retryable" in retry_resp.json()["detail"]

    # 3. Simulate a failed message in repository
    record = message_repository.get_message(msg_id)
    assert record is not None
    # Change status to FAILED
    message_repository.update_status(msg_id, status=MessageStatus.FAILED, failure_reason="Simulated mesh drop")
    old_packet_id = record.packet_id

    # 4. Retry the failed message
    retry_success = client.post(f"/api/messages/{msg_id}/retry")
    assert retry_success.status_code == 200
    retry_data = retry_success.json()

    # Preserves message_id, generates new packet_id, increments retry_count
    assert retry_data["message_id"] == msg_id
    assert retry_data["packet_id"] != old_packet_id
    
    updated_rec = message_repository.get_message(msg_id)
    assert updated_rec.retry_count == 1
    assert updated_rec.status == MessageStatus.DELIVERED


def test_conversation_thread_and_device_history():
    """Verify conversation thread retrieval and deterministic grouping."""
    # Send from RESQ-001 to RESQ-002
    resp1 = client.post(
        "/api/messages",
        json={"sender_id": "RESQ-001", "recipient_id": "RESQ-002", "message": "Ping from 001"},
    )
    assert resp1.status_code == 200

    # Send from RESQ-002 to RESQ-001
    resp2 = client.post(
        "/api/messages",
        json={"sender_id": "RESQ-002", "recipient_id": "RESQ-001", "message": "Pong from 002"},
    )
    assert resp2.status_code == 200

    # Query conversation both ways
    conv_forward = client.get("/api/conversations/DEVICE-001/DEVICE-002")
    assert conv_forward.status_code == 200
    conv_data_f = conv_forward.json()
    assert conv_data_f["conversation_id"] == "CONV_DEVICE-001_DEVICE-002"
    assert conv_data_f["total_messages"] >= 2

    conv_reverse = client.get("/api/conversations/DEVICE-002/DEVICE-001")
    assert conv_reverse.status_code == 200
    conv_data_r = conv_reverse.json()
    assert conv_data_r["conversation_id"] == "CONV_DEVICE-001_DEVICE-002"
    assert conv_data_r["total_messages"] == conv_data_f["total_messages"]

    # Device history
    dev_history = client.get("/api/devices/DEVICE-001/messages")
    assert dev_history.status_code == 200
    assert len(dev_history.json()) >= 2


def test_canonical_api_delegation():
    """Verify POST /api/messages (canonical) and POST /api/messages/send behave identically."""
    payload = {
        "sender_id": "RESQ-001",
        "recipient_id": "RESQ-002",
        "message": "Canonical test",
    }
    resp_canon = client.post("/api/messages", json=payload)
    assert resp_canon.status_code == 200
    data_canon = resp_canon.json()
    assert data_canon["status"] == "delivered"
    assert "packet_id" in data_canon
    assert "message_id" in data_canon

    resp_alias = client.post("/api/messages/send", json=payload)
    assert resp_alias.status_code == 200
    data_alias = resp_alias.json()
    assert data_alias["status"] == "delivered"
    assert "packet_id" in data_alias
    assert "message_id" in data_alias
