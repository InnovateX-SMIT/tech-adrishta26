import base64
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.app.core.crypto import (
    canonicalize_payload,
    decrypt_authenticated,
    DecryptionAuthenticationError,
    verify_signature,
    decode_ed25519_public_key_b64,
)
from backend.app.core.mesh_network import NoRouteError
from backend.app.core.mesh_node import MeshNode
from backend.app.main import app
from backend.app.models.crypto import EncryptionEnvelope
from backend.app.models.registry import MemberStatus, RegisterMemberRequest, RescueMember
from backend.app.services.crypto_service import crypto_service
from backend.app.services.message_service import (
    MemberMissingKeysError,
    MemberNotActiveError,
    MeshNodeNotFoundError,
    message_service,
)
from backend.app.services.mesh_service import get_network, reset_network
from backend.app.services.registry_service import MemberNotFoundError, registry_service
from backend.app.storage.json_store import save_json

client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_secure_transmission_env(tmp_path: Path):
    """Isolates registry, keys directory, and mesh network for all tests."""
    temp_registry = tmp_path / "registry.json"
    save_json(temp_registry, {"version": 1, "members": []})

    temp_keys = tmp_path / "keys"
    temp_keys.mkdir(parents=True, exist_ok=True)

    orig_reg_path = registry_service.registry_path
    orig_crypto_keys = crypto_service.keys_dir

    registry_service.registry_path = temp_registry
    crypto_service.keys_dir = temp_keys
    crypto_service.registry_service = registry_service

    reset_network()

    yield tmp_path

    registry_service.registry_path = orig_reg_path
    crypto_service.keys_dir = orig_crypto_keys
    crypto_service.registry_service = registry_service
    reset_network()


def create_initialized_member(name: str, team: str = "Rescue Unit A", role: str = "Responder") -> RescueMember:
    """Helper: registers a member and initializes Ed25519 & X25519 keys."""
    req = RegisterMemberRequest(name=name, team=team, role=role)
    member = registry_service.register_member(req)
    crypto_service.initialize_device_keys(member.device_id)
    return registry_service.get_member_by_device_id(member.device_id)


def setup_direct_mesh_nodes(node_a_id: str, node_b_id: str):
    """Helper: registers two connected nodes in the active mesh network."""
    net = get_network()
    net.add_node(MeshNode(node_a_id))
    net.add_node(MeshNode(node_b_id))
    net.connect_nodes(node_a_id, node_b_id)


# ===========================================================================
# 1. Basic Security Tests
# ===========================================================================


def test_secure_payload_contains_ciphertext():
    """1. Secure payload contains valid Base64 ciphertext with tag."""
    sender = create_initialized_member("Sender Unit")
    recipient = create_initialized_member("Recipient Unit")
    setup_direct_mesh_nodes(sender.device_id, recipient.device_id)

    resp = message_service.send_secure_message(
        sender_id=sender.rescue_id,
        recipient_id=recipient.rescue_id,
        message="Critical evacuation alert",
    )

    ct = resp.payload.ciphertext
    assert isinstance(ct, str)
    raw_ct = base64.b64decode(ct)
    assert len(raw_ct) >= 16  # Must contain at least the 16-byte Poly1305 tag


def test_secure_payload_contains_signature():
    """2. Secure payload contains valid Base64 64-byte Ed25519 signature."""
    sender = create_initialized_member("Sender Unit")
    recipient = create_initialized_member("Recipient Unit")
    setup_direct_mesh_nodes(sender.device_id, recipient.device_id)

    resp = message_service.send_secure_message(
        sender_id=sender.rescue_id,
        recipient_id=recipient.rescue_id,
        message="Critical evacuation alert",
    )

    sig = resp.payload.signature
    assert isinstance(sig, str)
    raw_sig = base64.b64decode(sig)
    assert len(raw_sig) == 64  # Ed25519 signature is exactly 64 bytes


def test_secure_payload_contains_nonce_salt_ephemeral_key():
    """3. Secure payload contains nonce, salt, and ephemeral public key."""
    sender = create_initialized_member("Sender Unit")
    recipient = create_initialized_member("Recipient Unit")
    setup_direct_mesh_nodes(sender.device_id, recipient.device_id)

    resp = message_service.send_secure_message(
        sender_id=sender.rescue_id,
        recipient_id=recipient.rescue_id,
        message="Critical evacuation alert",
    )

    p = resp.payload
    assert len(base64.b64decode(p.nonce)) == 12
    assert len(base64.b64decode(p.salt)) == 16
    assert len(base64.b64decode(p.ephemeral_public_key)) == 32


def test_secure_payload_does_not_contain_plaintext():
    """4. Plaintext message is strictly omitted from the transmitted packet payload."""
    secret_text = "SECRET-EMERGENCY-PAYLOAD-9944"
    sender = create_initialized_member("Sender Unit")
    recipient = create_initialized_member("Recipient Unit")
    setup_direct_mesh_nodes(sender.device_id, recipient.device_id)

    resp = message_service.send_secure_message(
        sender_id=sender.rescue_id,
        recipient_id=recipient.rescue_id,
        message=secret_text,
    )

    # Inspect the delivered packet in recipient's inbox
    net = get_network()
    delivered_pkt = net.nodes[recipient.device_id].inbox[0]

    # Verify plaintext is absent from payload dict and its string representation
    assert secret_text not in str(delivered_pkt.payload)
    assert secret_text not in str(resp.model_dump())
    assert "message" not in delivered_pkt.payload
    assert "plaintext" not in delivered_pkt.payload


# ===========================================================================
# 2. Cryptography & Verification Tests
# ===========================================================================


def test_recipient_can_decrypt_successfully():
    """5. Recipient can decrypt ciphertext with their private encryption key."""
    original_message = "Distress call: 3 responders isolated on ridge."
    sender = create_initialized_member("Sender Unit")
    recipient = create_initialized_member("Recipient Unit")
    setup_direct_mesh_nodes(sender.device_id, recipient.device_id)

    resp = message_service.send_secure_message(
        sender_id=sender.rescue_id,
        recipient_id=recipient.rescue_id,
        message=original_message,
    )

    p = resp.payload
    recipient_priv_key = crypto_service.load_device_encryption_private_key(recipient.device_id)

    envelope = EncryptionEnvelope(
        version=p.version,
        key_agreement=p.key_agreement,  # type: ignore[arg-type]
        kdf=p.kdf,  # type: ignore[arg-type]
        cipher=p.cipher,  # type: ignore[arg-type]
        ephemeral_public_key=p.ephemeral_public_key,
        salt=p.salt,
        nonce=p.nonce,
        ciphertext=p.ciphertext,
    )

    decrypted_bytes = decrypt_authenticated(recipient_priv_key, envelope)
    assert decrypted_bytes.decode("utf-8") == original_message


def test_wrong_recipient_cannot_decrypt():
    """6. Wrong recipient private key cannot decrypt the ciphertext."""
    sender = create_initialized_member("Sender Unit")
    recipient = create_initialized_member("Recipient Unit")
    eavesdropper = create_initialized_member("Eavesdropper Unit")
    setup_direct_mesh_nodes(sender.device_id, recipient.device_id)

    resp = message_service.send_secure_message(
        sender_id=sender.rescue_id,
        recipient_id=recipient.rescue_id,
        message="Sensitive coordinates: 37.7749, -122.4194",
    )

    p = resp.payload
    eavesdropper_priv_key = crypto_service.load_device_encryption_private_key(eavesdropper.device_id)

    envelope = EncryptionEnvelope(
        version=p.version,
        key_agreement=p.key_agreement,  # type: ignore[arg-type]
        kdf=p.kdf,  # type: ignore[arg-type]
        cipher=p.cipher,  # type: ignore[arg-type]
        ephemeral_public_key=p.ephemeral_public_key,
        salt=p.salt,
        nonce=p.nonce,
        ciphertext=p.ciphertext,
    )

    with pytest.raises(DecryptionAuthenticationError):
        decrypt_authenticated(eavesdropper_priv_key, envelope)


def test_valid_signature_verifies():
    """7. Valid signature verifies against sender's Ed25519 public key."""
    sender = create_initialized_member("Sender Unit")
    recipient = create_initialized_member("Recipient Unit")
    setup_direct_mesh_nodes(sender.device_id, recipient.device_id)

    resp = message_service.send_secure_message(
        sender_id=sender.rescue_id,
        recipient_id=recipient.rescue_id,
        message="Integrity check test message",
    )

    p = resp.payload
    sender_pub_key = decode_ed25519_public_key_b64(sender.signing_public_key)

    canonical_dict = {
        "ciphertext": p.ciphertext,
        "ephemeral_public_key": p.ephemeral_public_key,
        "message_id": p.message_id,
        "nonce": p.nonce,
        "packet_id": p.packet_id,
        "recipient_device_id": p.recipient_device_id,
        "recipient_rescue_id": p.recipient_rescue_id,
        "salt": p.salt,
        "sender_device_id": p.sender_device_id,
        "sender_rescue_id": p.sender_rescue_id,
        "timestamp": p.timestamp,
        "version": p.version,
    }
    canonical_bytes = canonicalize_payload(canonical_dict)

    assert verify_signature(sender_pub_key, canonical_bytes, p.signature) is True


# ===========================================================================
# 3. Tampering & Integrity Tests
# ===========================================================================


def test_tampered_ciphertext_fails_signature():
    """8. Modified ciphertext causes signature verification failure and decryption failure."""
    sender = create_initialized_member("Sender Unit")
    recipient = create_initialized_member("Recipient Unit")
    setup_direct_mesh_nodes(sender.device_id, recipient.device_id)

    resp = message_service.send_secure_message(
        sender_id=sender.rescue_id,
        recipient_id=recipient.rescue_id,
        message="Tamper test",
    )

    p = resp.payload
    sender_pub_key = decode_ed25519_public_key_b64(sender.signing_public_key)

    # Tamper with one bit of ciphertext
    raw_ct = bytearray(base64.b64decode(p.ciphertext))
    raw_ct[0] ^= 0x01
    tampered_ct = base64.b64encode(raw_ct).decode("utf-8")

    canonical_dict = {
        "ciphertext": tampered_ct,
        "ephemeral_public_key": p.ephemeral_public_key,
        "message_id": p.message_id,
        "nonce": p.nonce,
        "packet_id": p.packet_id,
        "recipient_device_id": p.recipient_device_id,
        "recipient_rescue_id": p.recipient_rescue_id,
        "salt": p.salt,
        "sender_device_id": p.sender_device_id,
        "sender_rescue_id": p.sender_rescue_id,
        "timestamp": p.timestamp,
        "version": p.version,
    }
    canonical_bytes = canonicalize_payload(canonical_dict)

    # Signature verification must fail
    assert verify_signature(sender_pub_key, canonical_bytes, p.signature) is False


def test_tampered_recipient_id_fails_signature():
    """9. Modified recipient ID causes signature verification failure."""
    sender = create_initialized_member("Sender Unit")
    recipient = create_initialized_member("Recipient Unit")
    setup_direct_mesh_nodes(sender.device_id, recipient.device_id)

    resp = message_service.send_secure_message(
        sender_id=sender.rescue_id,
        recipient_id=recipient.rescue_id,
        message="Tamper recipient test",
    )

    p = resp.payload
    sender_pub_key = decode_ed25519_public_key_b64(sender.signing_public_key)

    canonical_dict = {
        "ciphertext": p.ciphertext,
        "ephemeral_public_key": p.ephemeral_public_key,
        "message_id": p.message_id,
        "nonce": p.nonce,
        "packet_id": p.packet_id,
        "recipient_device_id": "DEVICE-999-TAMPERED",
        "recipient_rescue_id": p.recipient_rescue_id,
        "salt": p.salt,
        "sender_device_id": p.sender_device_id,
        "sender_rescue_id": p.sender_rescue_id,
        "timestamp": p.timestamp,
        "version": p.version,
    }
    canonical_bytes = canonicalize_payload(canonical_dict)
    assert verify_signature(sender_pub_key, canonical_bytes, p.signature) is False


def test_tampered_sender_id_fails_signature():
    """10. Modified sender ID causes signature verification failure."""
    sender = create_initialized_member("Sender Unit")
    recipient = create_initialized_member("Recipient Unit")
    setup_direct_mesh_nodes(sender.device_id, recipient.device_id)

    resp = message_service.send_secure_message(
        sender_id=sender.rescue_id,
        recipient_id=recipient.rescue_id,
        message="Tamper sender test",
    )

    p = resp.payload
    sender_pub_key = decode_ed25519_public_key_b64(sender.signing_public_key)

    canonical_dict = {
        "ciphertext": p.ciphertext,
        "ephemeral_public_key": p.ephemeral_public_key,
        "message_id": p.message_id,
        "nonce": p.nonce,
        "packet_id": p.packet_id,
        "recipient_device_id": p.recipient_device_id,
        "recipient_rescue_id": p.recipient_rescue_id,
        "salt": p.salt,
        "sender_device_id": "DEVICE-000-IMPOSTOR",
        "sender_rescue_id": p.sender_rescue_id,
        "timestamp": p.timestamp,
        "version": p.version,
    }
    canonical_bytes = canonicalize_payload(canonical_dict)
    assert verify_signature(sender_pub_key, canonical_bytes, p.signature) is False


def test_tampered_nonce_or_salt_fails_signature():
    """11. Modified nonce or salt causes signature verification failure."""
    sender = create_initialized_member("Sender Unit")
    recipient = create_initialized_member("Recipient Unit")
    setup_direct_mesh_nodes(sender.device_id, recipient.device_id)

    resp = message_service.send_secure_message(
        sender_id=sender.rescue_id,
        recipient_id=recipient.rescue_id,
        message="Tamper nonce test",
    )

    p = resp.payload
    sender_pub_key = decode_ed25519_public_key_b64(sender.signing_public_key)

    # Tamper with nonce
    raw_nonce = bytearray(base64.b64decode(p.nonce))
    raw_nonce[0] ^= 0xFF
    tampered_nonce = base64.b64encode(raw_nonce).decode("utf-8")

    canonical_dict = {
        "ciphertext": p.ciphertext,
        "ephemeral_public_key": p.ephemeral_public_key,
        "message_id": p.message_id,
        "nonce": tampered_nonce,
        "packet_id": p.packet_id,
        "recipient_device_id": p.recipient_device_id,
        "recipient_rescue_id": p.recipient_rescue_id,
        "salt": p.salt,
        "sender_device_id": p.sender_device_id,
        "sender_rescue_id": p.sender_rescue_id,
        "timestamp": p.timestamp,
        "version": p.version,
    }
    canonical_bytes = canonicalize_payload(canonical_dict)
    assert verify_signature(sender_pub_key, canonical_bytes, p.signature) is False


# ===========================================================================
# 4. Mesh Forwarding & Attacker Capture Tests
# ===========================================================================


def test_secure_packet_traverses_multiple_hops():
    """12. Secure packet traverses multi-hop mesh topology with full hop logging."""
    sender = create_initialized_member("Sender Unit")
    relay = create_initialized_member("Relay Unit")
    recipient = create_initialized_member("Recipient Unit")

    # Topology: sender <-> relay <-> recipient
    net = get_network()
    net.add_node(MeshNode(sender.device_id))
    net.add_node(MeshNode(relay.device_id))
    net.add_node(MeshNode(recipient.device_id))
    net.connect_nodes(sender.device_id, relay.device_id)
    net.connect_nodes(relay.device_id, recipient.device_id)

    resp = message_service.send_secure_message(
        sender_id=sender.rescue_id,
        recipient_id=recipient.rescue_id,
        message="Multi-hop secure dispatch",
    )

    assert len(resp.hop_log) == 2
    assert resp.hop_log[0].from_node == sender.device_id
    assert resp.hop_log[0].to_node == relay.device_id
    assert resp.hop_log[1].from_node == relay.device_id
    assert resp.hop_log[1].to_node == recipient.device_id


def test_secure_packet_arrives_in_recipient_inbox():
    """13. Packet arrives intact in recipient node's inbox."""
    sender = create_initialized_member("Sender Unit")
    recipient = create_initialized_member("Recipient Unit")
    setup_direct_mesh_nodes(sender.device_id, recipient.device_id)

    message_service.send_secure_message(
        sender_id=sender.rescue_id,
        recipient_id=recipient.rescue_id,
        message="Inbox verification test",
    )

    net = get_network()
    inbox = net.nodes[recipient.device_id].inbox
    assert len(inbox) == 1
    assert inbox[0].sender_id == sender.device_id
    assert inbox[0].receiver_id == recipient.device_id
    assert "ciphertext" in inbox[0].payload


def test_attacker_can_capture_packet():
    """14. Attacker node adjacent to the transmission path captures the packet."""
    sender = create_initialized_member("Sender Unit")
    relay = create_initialized_member("Relay Unit")
    recipient = create_initialized_member("Recipient Unit")

    net = get_network()
    net.add_node(MeshNode(sender.device_id))
    net.add_node(MeshNode(relay.device_id))
    net.add_node(MeshNode(recipient.device_id))
    net.add_node(MeshNode("ATTACKER_SNIFFER", is_attacker=True))

    net.connect_nodes(sender.device_id, relay.device_id)
    net.connect_nodes(relay.device_id, recipient.device_id)
    net.connect_nodes("ATTACKER_SNIFFER", relay.device_id)  # Sniffer adjacent to relay

    message_service.send_secure_message(
        sender_id=sender.rescue_id,
        recipient_id=recipient.rescue_id,
        message="Intercept me if you can",
    )

    attacker = net.nodes["ATTACKER_SNIFFER"]
    assert len(attacker.captured_packets) >= 1
    captured_pkt = attacker.captured_packets[0]
    assert captured_pkt.sender_id == sender.device_id
    assert captured_pkt.receiver_id == recipient.device_id


def test_attacker_captured_packet_contains_no_plaintext():
    """15. Attacker captured packet contains strictly ciphertext and no plaintext."""
    secret_text = "SECRET_CLASSIFIED_EVACUATION_ORDER_88"
    sender = create_initialized_member("Sender Unit")
    recipient = create_initialized_member("Recipient Unit")

    net = get_network()
    net.add_node(MeshNode(sender.device_id))
    net.add_node(MeshNode(recipient.device_id))
    net.add_node(MeshNode("SNIFFER", is_attacker=True))

    net.connect_nodes(sender.device_id, recipient.device_id)
    net.connect_nodes("SNIFFER", sender.device_id)

    message_service.send_secure_message(
        sender_id=sender.rescue_id,
        recipient_id=recipient.rescue_id,
        message=secret_text,
    )

    attacker = net.nodes["SNIFFER"]
    assert len(attacker.captured_packets) >= 1
    captured_payload = attacker.captured_packets[0].payload

    assert secret_text not in str(captured_payload)
    assert "message" not in captured_payload
    assert "plaintext" not in captured_payload
    assert "ciphertext" in captured_payload


# ===========================================================================
# 5. Registry & Authorization Tests
# ===========================================================================


def test_unknown_sender_rejected():
    """16. Unknown sender is rejected with MemberNotFoundError."""
    recipient = create_initialized_member("Recipient Unit")
    setup_direct_mesh_nodes("DEVICE-001", recipient.device_id)

    with pytest.raises(MemberNotFoundError):
        message_service.send_secure_message(
            sender_id="RESQ-UNKNOWN",
            recipient_id=recipient.rescue_id,
            message="Hello",
        )


def test_unknown_recipient_rejected():
    """17. Unknown recipient is rejected with MemberNotFoundError."""
    sender = create_initialized_member("Sender Unit")
    setup_direct_mesh_nodes(sender.device_id, "DEVICE-999")

    with pytest.raises(MemberNotFoundError):
        message_service.send_secure_message(
            sender_id=sender.rescue_id,
            recipient_id="RESQ-UNKNOWN",
            message="Hello",
        )


def test_revoked_sender_rejected():
    """18. Revoked sender is rejected with MemberNotActiveError."""
    sender = create_initialized_member("Revoked Sender")
    recipient = create_initialized_member("Recipient Unit")
    setup_direct_mesh_nodes(sender.device_id, recipient.device_id)

    registry_service.revoke_member(sender.rescue_id)

    with pytest.raises(MemberNotActiveError) as exc_info:
        message_service.send_secure_message(
            sender_id=sender.rescue_id,
            recipient_id=recipient.rescue_id,
            message="Unauthorized broadcast",
        )
    assert "revoked" in str(exc_info.value).lower()


def test_revoked_recipient_rejected():
    """19. Revoked recipient is rejected with MemberNotActiveError."""
    sender = create_initialized_member("Sender Unit")
    recipient = create_initialized_member("Revoked Recipient")
    setup_direct_mesh_nodes(sender.device_id, recipient.device_id)

    registry_service.revoke_member(recipient.rescue_id)

    with pytest.raises(MemberNotActiveError) as exc_info:
        message_service.send_secure_message(
            sender_id=sender.rescue_id,
            recipient_id=recipient.rescue_id,
            message="Message to revoked unit",
        )
    assert "revoked" in str(exc_info.value).lower()


def test_missing_uninitialized_keys_rejected():
    """20. Sender or recipient with missing public/private keys is rejected."""
    # Register member without initializing keys
    uninit_member = registry_service.register_member(
        RegisterMemberRequest(name="Uninitialized Unit", team="Ops", role="Medic")
    )
    recipient = create_initialized_member("Recipient Unit")
    setup_direct_mesh_nodes(uninit_member.device_id, recipient.device_id)

    with pytest.raises(MemberMissingKeysError):
        message_service.send_secure_message(
            sender_id=uninit_member.rescue_id,
            recipient_id=recipient.rescue_id,
            message="Cannot sign",
        )


# ===========================================================================
# 6. Routing Tests
# ===========================================================================


def test_unreachable_recipient_produces_controlled_failure():
    """21. Unreachable mesh destination produces NoRouteError."""
    sender = create_initialized_member("Sender Unit")
    recipient = create_initialized_member("Isolated Unit")

    net = get_network()
    net.add_node(MeshNode(sender.device_id))
    net.add_node(MeshNode(recipient.device_id))
    # No edges connected between them

    with pytest.raises(NoRouteError):
        message_service.send_secure_message(
            sender_id=sender.rescue_id,
            recipient_id=recipient.rescue_id,
            message="Unreachable packet",
        )


# ===========================================================================
# 7. FastAPI REST API Integration Tests (POST /api/messages/send)
# ===========================================================================


def test_api_send_secure_message_success():
    """API endpoint returns 200 with encrypted payload and no plaintext."""
    sender = create_initialized_member("API Sender")
    recipient = create_initialized_member("API Recipient")
    setup_direct_mesh_nodes(sender.device_id, recipient.device_id)

    payload = {
        "sender_id": sender.rescue_id,
        "recipient_id": recipient.rescue_id,
        "message": "API emergency transmission test",
        "priority": "HIGH",
    }
    resp = client.post("/api/messages/send", json=payload)
    assert resp.status_code == 200

    data = resp.json()
    assert data["sender_id"] == sender.rescue_id
    assert data["recipient_id"] == recipient.rescue_id
    assert data["status"] == "delivered"
    assert len(data["hop_log"]) == 1

    # Security verification: plaintext message must NOT be returned in API response
    assert "message" not in data
    assert "plaintext" not in data
    assert "API emergency transmission test" not in str(data)

    # Cryptographic fields must be present
    secure_p = data["payload"]
    assert secure_p["sender_device_id"] == sender.device_id
    assert secure_p["recipient_device_id"] == recipient.device_id
    assert "ciphertext" in secure_p
    assert "signature" in secure_p
    assert "ephemeral_public_key" in secure_p


def test_api_send_with_device_ids():
    """API endpoint accepts Device IDs as well as Rescue IDs."""
    sender = create_initialized_member("Device ID Sender")
    recipient = create_initialized_member("Device ID Recipient")
    setup_direct_mesh_nodes(sender.device_id, recipient.device_id)

    payload = {
        "sender_id": sender.device_id,
        "recipient_id": recipient.device_id,
        "message": "Device ID routing test",
    }
    resp = client.post("/api/messages/send", json=payload)
    assert resp.status_code == 200
    assert resp.json()["status"] == "delivered"


def test_api_send_unknown_sender_returns_404():
    recipient = create_initialized_member("API Recipient")
    setup_direct_mesh_nodes("DEVICE-001", recipient.device_id)

    payload = {
        "sender_id": "RESQ-GHOST-999",
        "recipient_id": recipient.rescue_id,
        "message": "Ghost test",
    }
    resp = client.post("/api/messages/send", json=payload)
    assert resp.status_code == 404


def test_api_send_revoked_sender_returns_400():
    sender = create_initialized_member("Revoked API Sender")
    recipient = create_initialized_member("API Recipient")
    setup_direct_mesh_nodes(sender.device_id, recipient.device_id)

    registry_service.revoke_member(sender.rescue_id)

    payload = {
        "sender_id": sender.rescue_id,
        "recipient_id": recipient.rescue_id,
        "message": "Blocked message",
    }
    resp = client.post("/api/messages/send", json=payload)
    assert resp.status_code == 400
    assert "revoked" in resp.json()["detail"].lower()


def test_api_send_no_route_returns_422():
    sender = create_initialized_member("Island A")
    recipient = create_initialized_member("Island B")

    net = get_network()
    net.add_node(MeshNode(sender.device_id))
    net.add_node(MeshNode(recipient.device_id))
    # Disconnected

    payload = {
        "sender_id": sender.rescue_id,
        "recipient_id": recipient.rescue_id,
        "message": "Disconnected test",
    }
    resp = client.post("/api/messages/send", json=payload)
    assert resp.status_code == 422
    assert "no route found" in resp.json()["detail"].lower()
