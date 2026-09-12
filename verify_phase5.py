"""
verify_phase5.py — Standalone verification script for Phase 5 Secure Message Transmission.
Executes core Phase 5 logic, cryptographic assertions, mesh routing, and security invariants.
Execute: python verify_phase5.py
"""

import base64
import os
import shutil
import sys
import tempfile
from pathlib import Path

# Add workspace to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

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
from backend.app.models.messages import (
    SendMessageRequest,
    SecureMessagePayload,
    SendMessageResponse,
)
from backend.app.models.registry import RegisterMemberRequest
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

errors = []


def check(name: str, cond: bool, msg: str = ""):
    if cond:
        print(f"  OK   {name}")
    else:
        print(f"  FAIL {name}: {msg}")
        errors.append(name)


print("=== RESQ Phase 5 Secure Message Transmission Verification ===\n")

# Setup isolated environment
temp_dir = Path(tempfile.mkdtemp(prefix="resq_phase5_test_"))
try:
    temp_reg = temp_dir / "registry.json"
    save_json(temp_reg, {"version": 1, "members": []})
    temp_keys = temp_dir / "keys"
    temp_keys.mkdir(parents=True, exist_ok=True)

    orig_reg = registry_service.registry_path
    orig_keys = crypto_service.keys_dir

    registry_service.registry_path = temp_reg
    crypto_service.keys_dir = temp_keys
    crypto_service.registry_service = registry_service

    reset_network()

    # 1. Register & Initialize 3 members (Alice, Bob, Carol)
    m_alice = registry_service.register_member(RegisterMemberRequest(name="Alice", team="Alpha", role="Lead"))
    crypto_service.initialize_device_keys(m_alice.device_id)
    alice = registry_service.get_member_by_device_id(m_alice.device_id)

    m_bob = registry_service.register_member(RegisterMemberRequest(name="Bob", team="Alpha", role="Medic"))
    crypto_service.initialize_device_keys(m_bob.device_id)
    bob = registry_service.get_member_by_device_id(m_bob.device_id)

    m_carol = registry_service.register_member(RegisterMemberRequest(name="Carol", team="Bravo", role="Relay"))
    crypto_service.initialize_device_keys(m_carol.device_id)
    carol = registry_service.get_member_by_device_id(m_carol.device_id)

    # 2. Setup Mesh Topology: Alice <-> Carol <-> Bob, plus Attacker adjacent to Carol
    net = get_network()
    net.add_node(MeshNode(alice.device_id))
    net.add_node(MeshNode(carol.device_id))
    net.add_node(MeshNode(bob.device_id))
    net.add_node(MeshNode("ATTACKER_SNIFFER", is_attacker=True))

    net.connect_nodes(alice.device_id, carol.device_id)
    net.connect_nodes(carol.device_id, bob.device_id)
    net.connect_nodes("ATTACKER_SNIFFER", carol.device_id)

    # -------------------------------------------------------------
    # Test Suite
    # -------------------------------------------------------------
    secret_text = "EMERGENCY: Trapped personnel at coordinates 28.6139, 77.2090. Medical assistance required."

    # Send secure message Alice -> Bob
    resp = message_service.send_secure_message(
        sender_id=alice.rescue_id,
        recipient_id=bob.rescue_id,
        message=secret_text,
        priority="CRITICAL",
    )

    # 1. Basic Security Checks
    p = resp.payload
    check("Payload has ciphertext", isinstance(p.ciphertext, str) and len(base64.b64decode(p.ciphertext)) >= 16)
    check("Payload has signature", isinstance(p.signature, str) and len(base64.b64decode(p.signature)) == 64)
    check("Payload has 12-byte nonce", len(base64.b64decode(p.nonce)) == 12)
    check("Payload has 16-byte salt", len(base64.b64decode(p.salt)) == 16)
    check("Payload has 32-byte ephemeral pubkey", len(base64.b64decode(p.ephemeral_public_key)) == 32)
    check("Payload does NOT contain plaintext", secret_text not in str(p.model_dump()))

    # 2. Cryptographic Decryption by Intended Recipient (Bob)
    bob_priv_key = crypto_service.load_device_encryption_private_key(bob.device_id)
    env = EncryptionEnvelope(
        version=p.version,
        key_agreement=p.key_agreement,
        kdf=p.kdf,
        cipher=p.cipher,
        ephemeral_public_key=p.ephemeral_public_key,
        salt=p.salt,
        nonce=p.nonce,
        ciphertext=p.ciphertext,
    )
    decrypted = decrypt_authenticated(bob_priv_key, env).decode("utf-8")
    check("Recipient successfully decrypts original plaintext", decrypted == secret_text)

    # 3. Cryptographic Decryption Rejection by Wrong Key (Alice's or Carol's key)
    alice_enc_priv = crypto_service.load_device_encryption_private_key(alice.device_id)
    try:
        decrypt_authenticated(alice_enc_priv, env)
        check("Wrong key decryption fails", False, "Should have raised DecryptionAuthenticationError")
    except DecryptionAuthenticationError:
        check("Wrong key decryption fails", True)

    # 4. Digital Signature Verification
    alice_signing_pub = decode_ed25519_public_key_b64(alice.signing_public_key)
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
    valid_sig = verify_signature(alice_signing_pub, canonical_bytes, p.signature)
    check("Valid Ed25519 signature verifies", valid_sig is True)

    # 5. Tampering Rejection
    tampered_dict = dict(canonical_dict)
    tampered_dict["recipient_device_id"] = "DEVICE-MALICIOUS"
    tampered_bytes = canonicalize_payload(tampered_dict)
    check("Tampered metadata fails signature verification", verify_signature(alice_signing_pub, tampered_bytes, p.signature) is False)

    # 6. Multi-Hop Forwarding & Hop Log
    check("Packet traversed 2 hops (Alice -> Carol -> Bob)", len(resp.hop_log) == 2)
    check("Hop 1 is Alice -> Carol", resp.hop_log[0].from_node == alice.device_id and resp.hop_log[0].to_node == carol.device_id)
    check("Hop 2 is Carol -> Bob", resp.hop_log[1].from_node == carol.device_id and resp.hop_log[1].to_node == bob.device_id)

    # 7. Recipient Inbox Delivery
    bob_inbox = net.nodes[bob.device_id].inbox
    check("Delivered packet is in Bob's inbox", len(bob_inbox) >= 1 and bob_inbox[0].packet_id == resp.packet_id)

    # 8. Attacker Sniffing Simulation & Zero Plaintext Invariant
    attacker = net.nodes["ATTACKER_SNIFFER"]
    check("Attacker passively captured packet from adjacent hop", len(attacker.captured_packets) >= 1)
    captured_payload = attacker.captured_packets[0].payload
    check("Attacker packet contains NO plaintext", secret_text not in str(captured_payload))
    check("Attacker packet contains ciphertext", "ciphertext" in captured_payload)

    # 9. Authorization Checks
    # Revoke Alice -> Alice cannot send
    registry_service.revoke_member(alice.rescue_id)
    try:
        message_service.send_secure_message(alice.rescue_id, bob.rescue_id, "Should fail")
        check("Revoked sender rejected", False, "Should raise MemberNotActiveError")
    except MemberNotActiveError:
        check("Revoked sender rejected", True)

    # Unknown sender
    try:
        message_service.send_secure_message("RESQ-NONEXISTENT", bob.rescue_id, "Should fail")
        check("Unknown sender rejected", False, "Should raise MemberNotFoundError")
    except MemberNotFoundError:
        check("Unknown sender rejected", True)

    # 10. FastAPI Endpoint Integration
    client = TestClient(app)
    api_resp = client.post(
        "/api/messages/send",
        json={
            "sender_id": carol.rescue_id,
            "recipient_id": bob.rescue_id,
            "message": "REST API secure message test",
        },
    )
    check("API POST /api/messages/send returns 200", api_resp.status_code == 200, f"Status: {api_resp.status_code}")
    api_data = api_resp.json()
    check("API response does NOT contain plaintext message", "REST API secure message test" not in str(api_data))
    check("API response contains delivered status", api_data["status"] == "delivered")
    check("API response contains encrypted payload", "ciphertext" in api_data["payload"] and "signature" in api_data["payload"])

finally:
    # Teardown
    registry_service.registry_path = orig_reg
    crypto_service.keys_dir = orig_keys
    crypto_service.registry_service = registry_service
    reset_network()
    shutil.rmtree(temp_dir, ignore_errors=True)

print(f"\n=== Verification Summary: {len(errors)} Failures ===")
if not errors:
    print("ALL 19 PHASE 5 SECURITY & INTEGRATION CHECKS PASSED PERFECTLY!")
    sys.exit(0)
else:
    print(f"Failures: {errors}")
    sys.exit(1)
